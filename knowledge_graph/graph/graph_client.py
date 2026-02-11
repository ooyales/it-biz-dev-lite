#!/usr/bin/env python3
"""
Knowledge Graph Client — SQLite + NetworkX
Drop-in replacement for neo4j_client.py.
Same class name and method signatures so consumers need only import changes.
"""

import sqlite3
import logging
import json
import hashlib
import os
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default DB path — data/contacts.db relative to project root
_DEFAULT_DB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'data', 'contacts.db'
)


class KnowledgeGraphClient:
    """SQLite + NetworkX knowledge graph client for contact management.

    Drop-in replacement for the former Neo4j-based client.
    All graph nodes/edges are persisted in SQLite.
    NetworkX is used for traversal queries (shortest path, subgraph).
    """

    def __init__(self, db_path: str = None, **kwargs):
        """Initialise connection to SQLite.

        Accepts **kwargs so callers that still pass uri=/user=/password=
        keyword arguments won't break — those args are simply ignored.
        """
        self.db_path = db_path or _DEFAULT_DB
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._graph = None  # lazy NetworkX graph
        logger.info(f"KnowledgeGraphClient using SQLite at {self.db_path}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _rebuild_graph(self):
        """Build an in-memory NetworkX graph from SQLite edges."""
        if not HAS_NETWORKX:
            self._graph = None
            return
        G = nx.DiGraph()
        conn = self._conn()
        # Add person nodes
        for row in conn.execute("SELECT id, name, graph_id FROM contacts WHERE graph_id IS NOT NULL"):
            G.add_node(row['graph_id'], node_type='Person', name=row['name'], sqlite_id=row['id'])
        # Add organization nodes
        for row in conn.execute("SELECT id, name, type FROM organizations"):
            G.add_node(row['id'], node_type='Organization', name=row['name'], org_type=row['type'])
        # Add edges
        for row in conn.execute("SELECT from_id, to_id, rel_type, properties FROM graph_edges"):
            props = json.loads(row['properties']) if row['properties'] else {}
            G.add_edge(row['from_id'], row['to_id'], rel_type=row['rel_type'], **props)
        conn.close()
        self._graph = G

    @property
    def graph(self) -> Any:
        if self._graph is None:
            self._rebuild_graph()
        return self._graph

    def close(self):
        logger.info("KnowledgeGraphClient closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ========================================================================
    # SCHEMA INITIALISATION
    # ========================================================================
    def initialize_schema(self):
        """Create tables and indexes."""
        logger.info("Initializing graph schema (SQLite)...")
        conn = self._conn()

        conn.executescript("""
            CREATE TABLE IF NOT EXISTS organizations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                abbreviation TEXT,
                type TEXT,
                parent TEXT,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                contract_number TEXT,
                title TEXT,
                value REAL DEFAULT 0,
                award_date TEXT,
                agency TEXT,
                contractor_name TEXT,
                naics TEXT,
                source TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS graph_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_type TEXT NOT NULL,
                from_id TEXT NOT NULL,
                to_type TEXT NOT NULL,
                to_id TEXT NOT NULL,
                rel_type TEXT NOT NULL,
                properties TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_edges_from ON graph_edges(from_id, rel_type);
            CREATE INDEX IF NOT EXISTS idx_edges_to ON graph_edges(to_id, rel_type);
            CREATE INDEX IF NOT EXISTS idx_edges_rel ON graph_edges(rel_type);
            CREATE INDEX IF NOT EXISTS idx_contracts_agency ON contracts(agency);
            CREATE INDEX IF NOT EXISTS idx_contracts_naics ON contracts(naics);
            CREATE INDEX IF NOT EXISTS idx_contracts_contractor ON contracts(contractor_name);
            CREATE INDEX IF NOT EXISTS idx_orgs_name ON organizations(name);
        """)

        # Ensure contacts table has graph_id column
        try:
            conn.execute("ALTER TABLE contacts ADD COLUMN graph_id TEXT")
            logger.info("Added graph_id column to contacts")
        except sqlite3.OperationalError:
            pass  # already exists

        conn.commit()
        conn.close()
        logger.info("Schema initialization complete")

    # ========================================================================
    # PERSON OPERATIONS
    # ========================================================================
    def create_person(self, person_data: Dict[str, Any]) -> str:
        pid = person_data.get('id') or generate_person_id(
            person_data.get('name', ''), person_data.get('email')
        )
        conn = self._conn()
        now = datetime.now().isoformat()

        # Upsert into contacts
        existing = conn.execute(
            "SELECT id FROM contacts WHERE graph_id = ?", (pid,)
        ).fetchone()

        if existing:
            conn.execute("""
                UPDATE contacts SET
                    name = COALESCE(?, name),
                    email = COALESCE(?, email),
                    phone = COALESCE(?, phone),
                    title = COALESCE(?, title),
                    organization = COALESCE(?, organization),
                    source = COALESCE(?, source),
                    role = COALESCE(?, role),
                    agency = COALESCE(?, agency),
                    updated_at = ?
                WHERE graph_id = ?
            """, (
                person_data.get('name'), person_data.get('email'),
                person_data.get('phone'), person_data.get('title'),
                person_data.get('organization'), person_data.get('source'),
                person_data.get('role_type'), person_data.get('agency', person_data.get('organization')),
                now, pid
            ))
        else:
            # Map influence_level to relationship_strength
            strength_map = {
                'Very High': 'Strong', 'High': 'Strong',
                'Medium': 'Warm', 'Low': 'New'
            }
            strength = strength_map.get(person_data.get('influence_level'), 'New')

            conn.execute("""
                INSERT INTO contacts
                    (name, email, phone, title, organization, role, source,
                     relationship_strength, graph_id, agency, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                person_data.get('name', ''),
                person_data.get('email'),
                person_data.get('phone'),
                person_data.get('title'),
                person_data.get('organization'),
                person_data.get('role_type'),
                person_data.get('source'),
                strength,
                pid,
                person_data.get('agency', person_data.get('organization')),
                now, now
            ))

        conn.commit()
        conn.close()
        self._graph = None  # invalidate cache
        logger.info(f"Created/updated person: {person_data.get('name')} ({pid})")
        return pid

    def get_person(self, person_id: str) -> Optional[Dict]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM contacts WHERE graph_id = ?", (person_id,)
        ).fetchone()
        conn.close()
        if row:
            d = dict(row)
            d['id'] = d.get('graph_id', person_id)
            return d
        return None

    def find_person_by_email(self, email: str) -> Optional[Dict]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM contacts WHERE email = ?", (email,)
        ).fetchone()
        conn.close()
        if row:
            d = dict(row)
            d['id'] = d.get('graph_id', '')
            return d
        return None

    def search_people(self, name_query: str) -> List[Dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM contacts WHERE LOWER(name) LIKE ? LIMIT 20",
            (f"%{name_query.lower()}%",)
        ).fetchall()
        conn.close()
        results = []
        for row in rows:
            d = dict(row)
            d['id'] = d.get('graph_id', '')
            results.append(d)
        return results

    # ========================================================================
    # ORGANIZATION OPERATIONS
    # ========================================================================
    def create_organization(self, org_data: Dict[str, Any]) -> str:
        oid = org_data.get('id') or generate_org_id(org_data.get('name', ''))
        conn = self._conn()
        now = datetime.now().isoformat()

        conn.execute("""
            INSERT INTO organizations (id, name, abbreviation, type, parent, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = COALESCE(excluded.name, name),
                abbreviation = COALESCE(excluded.abbreviation, abbreviation),
                type = COALESCE(excluded.type, type),
                parent = COALESCE(excluded.parent, parent),
                source = COALESCE(excluded.source, source),
                updated_at = excluded.updated_at
        """, (
            oid, org_data.get('name', ''), org_data.get('abbreviation'),
            org_data.get('type'), org_data.get('parent'),
            org_data.get('source'), now, now
        ))

        conn.commit()
        conn.close()
        self._graph = None
        logger.info(f"Created/updated organization: {org_data.get('name')} ({oid})")
        return oid

    def get_organization(self, org_id: str) -> Optional[Dict]:
        conn = self._conn()
        row = conn.execute(
            "SELECT * FROM organizations WHERE id = ?", (org_id,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    # ========================================================================
    # CONTRACT OPERATIONS
    # ========================================================================
    def create_contract(self, contract_data: Dict[str, Any]) -> bool:
        """Create or update a contract record."""
        conn = self._conn()
        now = datetime.now().isoformat()
        name = contract_data.get('name', '')

        conn.execute("""
            INSERT INTO contracts
                (name, contract_number, title, value, award_date, agency,
                 contractor_name, naics, source, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                contract_number = COALESCE(excluded.contract_number, contract_number),
                title = COALESCE(excluded.title, title),
                value = excluded.value,
                award_date = COALESCE(excluded.award_date, award_date),
                agency = COALESCE(excluded.agency, agency),
                contractor_name = COALESCE(excluded.contractor_name, contractor_name),
                naics = COALESCE(excluded.naics, naics),
                source = COALESCE(excluded.source, source),
                description = COALESCE(excluded.description, description),
                updated_at = excluded.updated_at
        """, (
            name,
            contract_data.get('contract_number'),
            contract_data.get('title'),
            float(contract_data.get('value', 0) or 0),
            contract_data.get('award_date'),
            contract_data.get('agency'),
            contract_data.get('contractor_name'),
            contract_data.get('naics'),
            contract_data.get('source'),
            contract_data.get('description'),
            now, now
        ))

        conn.commit()
        conn.close()
        return True

    # ========================================================================
    # RELATIONSHIP OPERATIONS
    # ========================================================================
    def create_relationship(
        self, from_id: str, to_id: str, rel_type: str,
        properties: Dict[str, Any] = None,
        from_type: str = 'person', to_type: str = 'person'
    ) -> bool:
        if properties is None:
            properties = {}
        properties['created_at'] = datetime.now().isoformat()

        conn = self._conn()
        # Upsert: delete existing edge of same type between same nodes, then insert
        conn.execute(
            "DELETE FROM graph_edges WHERE from_id = ? AND to_id = ? AND rel_type = ?",
            (from_id, to_id, rel_type)
        )
        conn.execute("""
            INSERT INTO graph_edges (from_type, from_id, to_type, to_id, rel_type, properties)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (from_type, from_id, to_type, to_id, rel_type, json.dumps(properties)))

        conn.commit()
        conn.close()
        self._graph = None
        logger.info(f"Created relationship: {from_id} -{rel_type}-> {to_id}")
        return True

    def create_works_at(
        self, person_id: str, org_id: str,
        title: str = None, start_date: str = None,
        confidence: float = 1.0, source: str = None
    ):
        props = {
            'title': title, 'start_date': start_date,
            'confidence': confidence, 'source': source
        }
        return self.create_relationship(
            person_id, org_id, 'WORKS_AT', props,
            from_type='person', to_type='organization'
        )

    def create_reports_to(
        self, person_id: str, manager_id: str,
        since: str = None, source: str = None
    ):
        return self.create_relationship(
            person_id, manager_id, 'REPORTS_TO',
            {'since': since, 'source': source}
        )

    def create_interaction(
        self, person1_id: str, person2_id: str,
        interaction_type: str, date: str,
        outcome: str = None, notes: str = None
    ):
        return self.create_relationship(
            person1_id, person2_id, 'INTERACTED_WITH',
            {'type': interaction_type, 'date': date,
             'outcome': outcome, 'notes': notes}
        )

    # ========================================================================
    # QUERY OPERATIONS
    # ========================================================================
    def get_person_network(self, person_id: str, depth: int = 1) -> Dict:
        """Get person's network up to N hops using NetworkX."""
        if not HAS_NETWORKX or self.graph is None:
            return {'nodes': [], 'edges': []}

        G = self.graph
        if person_id not in G:
            return {'nodes': [], 'edges': []}

        # BFS to collect nodes within depth
        visited = {person_id}
        frontier = {person_id}
        for _ in range(depth):
            next_frontier = set()
            for node in frontier:
                for neighbor in set(G.successors(node)) | set(G.predecessors(node)):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_frontier.add(neighbor)
            frontier = next_frontier

        nodes = []
        for nid in visited:
            data = dict(G.nodes[nid])
            data['id'] = nid
            nodes.append(data)

        edges = []
        for u, v, data in G.edges(data=True):
            if u in visited and v in visited:
                edges.append({
                    'from': u, 'to': v,
                    'type': data.get('rel_type', ''),
                    'properties': {k: v_ for k, v_ in data.items() if k != 'rel_type'}
                })

        return {'nodes': nodes, 'edges': edges}

    def find_shortest_path(self, person1_id: str, person2_id: str) -> List[Dict]:
        """Find shortest path between two people using NetworkX."""
        if not HAS_NETWORKX or self.graph is None:
            return []

        G = self.graph.to_undirected()
        try:
            path_nodes = nx.shortest_path(G, person1_id, person2_id)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

        path_data = []
        for nid in path_nodes:
            data = dict(G.nodes[nid])
            data['id'] = nid
            path_data.append({'type': 'node', 'data': data})

        for i in range(len(path_nodes) - 1):
            u, v = path_nodes[i], path_nodes[i + 1]
            edata = G.edges[u, v] if G.has_edge(u, v) else {}
            path_data.append({'type': 'relationship', 'data': dict(edata)})

        return path_data

    def get_decision_makers_at_agency(self, agency_name: str) -> List[Dict]:
        conn = self._conn()
        rows = conn.execute("""
            SELECT c.*, o.name as org_name, o.type as org_type
            FROM contacts c
            LEFT JOIN graph_edges e ON e.from_id = c.graph_id AND e.rel_type = 'WORKS_AT'
            LEFT JOIN organizations o ON o.id = e.to_id
            WHERE c.role = 'Decision Maker'
              AND (o.name LIKE ? OR c.organization LIKE ? OR c.agency LIKE ?)
            ORDER BY c.relationship_strength DESC
        """, (f"%{agency_name}%", f"%{agency_name}%", f"%{agency_name}%")).fetchall()
        conn.close()

        results = []
        for row in rows:
            d = dict(row)
            results.append({
                'person': d,
                'organization': {
                    'name': d.get('org_name', d.get('organization', '')),
                    'type': d.get('org_type', '')
                }
            })
        return results

    def get_network_statistics(self) -> Dict:
        conn = self._conn()
        person_count = conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
        org_count = conn.execute("SELECT COUNT(*) FROM organizations").fetchone()[0]
        rel_count = conn.execute("SELECT COUNT(*) FROM graph_edges").fetchone()[0]
        dm_count = conn.execute(
            "SELECT COUNT(*) FROM contacts WHERE role = 'Decision Maker'"
        ).fetchone()[0]
        conn.close()

        return {
            'total_people': person_count,
            'total_organizations': org_count,
            'total_relationships': rel_count,
            'decision_makers': dm_count
        }

    # ========================================================================
    # CONTRACT QUERY OPERATIONS (used by competitive_intel, excel_exporter)
    # ========================================================================
    def get_contracts_for_org(self, org_id: str = None, org_name: str = None) -> List[Dict]:
        conn = self._conn()
        if org_name:
            rows = conn.execute(
                "SELECT * FROM contracts WHERE contractor_name = ? ORDER BY award_date DESC",
                (org_name,)
            ).fetchall()
        elif org_id:
            org = self.get_organization(org_id)
            if org:
                rows = conn.execute(
                    "SELECT * FROM contracts WHERE contractor_name = ? ORDER BY award_date DESC",
                    (org['name'],)
                ).fetchall()
            else:
                rows = []
        else:
            rows = []
        conn.close()
        return [dict(r) for r in rows]

    def get_contracts_by_agency(self, agency: str, naics: str = None, limit: int = 1000) -> List[Dict]:
        conn = self._conn()
        if naics:
            rows = conn.execute(
                "SELECT * FROM contracts WHERE agency LIKE ? AND naics = ? ORDER BY award_date DESC LIMIT ?",
                (f"%{agency}%", naics, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM contracts WHERE agency LIKE ? ORDER BY award_date DESC LIMIT ?",
                (f"%{agency}%", limit)
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_incumbents_at_agency(self, agency: str, naics: str = None, limit: int = 20) -> List[Dict]:
        conn = self._conn()
        if naics:
            rows = conn.execute("""
                SELECT contractor_name as company,
                       COUNT(*) as contract_count,
                       SUM(value) as total_value,
                       MAX(award_date) as latest_award
                FROM contracts
                WHERE agency LIKE ? AND naics = ?
                GROUP BY contractor_name
                ORDER BY total_value DESC
                LIMIT ?
            """, (f"%{agency}%", naics, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT contractor_name as company,
                       COUNT(*) as contract_count,
                       SUM(value) as total_value,
                       MAX(award_date) as latest_award
                FROM contracts
                WHERE agency LIKE ?
                GROUP BY contractor_name
                ORDER BY total_value DESC
                LIMIT ?
            """, (f"%{agency}%", limit)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_teaming_partners(self, agency: str = None, naics: str = None, min_contracts: int = 3) -> List[Dict]:
        conn = self._conn()
        conditions = ["1=1"]
        params: list = []
        if agency:
            conditions.append("agency LIKE ?")
            params.append(f"%{agency}%")
        if naics:
            conditions.append("naics = ?")
            params.append(naics)

        where = " AND ".join(conditions)
        rows = conn.execute(f"""
            SELECT contractor_name as company,
                   COUNT(*) as contract_count,
                   SUM(value) as total_value
            FROM contracts
            WHERE {where}
            GROUP BY contractor_name
            HAVING contract_count >= ?
            ORDER BY contract_count DESC
            LIMIT 50
        """, params + [min_contracts]).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_contract_count(self) -> int:
        conn = self._conn()
        count = conn.execute("SELECT COUNT(*) FROM contracts").fetchone()[0]
        conn.close()
        return count

    def get_all_contacts_with_orgs(self) -> List[Dict]:
        """Get all contacts with optional org relationship (for excel export)."""
        conn = self._conn()
        rows = conn.execute("""
            SELECT c.name, c.title, c.email, c.phone,
                   COALESCE(o.name, c.organization) as organization,
                   c.role as role_type,
                   c.relationship_strength as influence_level,
                   c.source, c.created_at as extracted_at
            FROM contacts c
            LEFT JOIN graph_edges e ON e.from_id = c.graph_id AND e.rel_type = 'WORKS_AT'
            LEFT JOIN organizations o ON o.id = e.to_id
            ORDER BY c.name
        """).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_all_orgs_with_counts(self) -> List[Dict]:
        """Get all organizations with contact and contract counts."""
        conn = self._conn()
        rows = conn.execute("""
            SELECT o.name, o.type,
                   (SELECT COUNT(*) FROM graph_edges e WHERE e.to_id = o.id AND e.rel_type = 'WORKS_AT') as people_count,
                   (SELECT COUNT(*) FROM contracts c WHERE c.contractor_name = o.name) as contract_count
            FROM organizations o
            ORDER BY people_count DESC, contract_count DESC
        """).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_all_contracts_with_orgs(self, limit: int = 1000) -> List[Dict]:
        """Get all contracts with contractor info (for excel export)."""
        conn = self._conn()
        rows = conn.execute("""
            SELECT contract_number as number, title, agency,
                   contractor_name as contractor, award_date,
                   value, naics, description
            FROM contracts
            ORDER BY award_date DESC
            LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ========================================================================
    # RESEARCH CACHE OPERATIONS (used by contact_research_agent)
    # ========================================================================
    def get_research_profile(self, name: str) -> Optional[Dict]:
        conn = self._conn()
        row = conn.execute(
            "SELECT research_profile FROM contacts WHERE name = ?", (name,)
        ).fetchone()
        conn.close()
        if row and row['research_profile']:
            try:
                return json.loads(row['research_profile'])
            except (json.JSONDecodeError, TypeError):
                pass
        return None

    def set_research_profile(self, name: str, profile: Dict) -> bool:
        conn = self._conn()
        profile_json = json.dumps(profile)
        cursor = conn.execute(
            "UPDATE contacts SET research_profile = ? WHERE name = ?",
            (profile_json, name)
        )
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        return updated

    def get_names_with_research(self) -> set:
        conn = self._conn()
        rows = conn.execute(
            "SELECT name FROM contacts WHERE research_profile IS NOT NULL AND research_profile != ''"
        ).fetchall()
        conn.close()
        return {row['name'] for row in rows}

    # ========================================================================
    # BULK OPERATIONS
    # ========================================================================
    def bulk_create_people(self, people: List[Dict]) -> int:
        count = 0
        for person in people:
            try:
                self.create_person(person)
                count += 1
            except Exception as e:
                logger.error(f"Error creating person {person.get('name')}: {e}")
        logger.info(f"Bulk created {count}/{len(people)} people")
        return count

    def clear_database(self):
        """Delete all graph data."""
        logger.warning("Clearing entire graph database...")
        conn = self._conn()
        conn.execute("DELETE FROM graph_edges")
        conn.execute("DELETE FROM organizations")
        conn.execute("DELETE FROM contracts")
        conn.commit()
        conn.close()
        self._graph = None
        logger.warning("Graph database cleared!")


# ============================================================================
# UTILITY FUNCTIONS (unchanged from neo4j_client.py)
# ============================================================================

def generate_person_id(name: str, email: str = None) -> str:
    if email:
        base = email.lower()
    else:
        base = name.lower().replace(' ', '_')
    hash_suffix = hashlib.md5(base.encode()).hexdigest()[:8]
    return f"person_{hash_suffix}"


def generate_org_id(org_name: str) -> str:
    base = org_name.lower().replace(' ', '_')
    hash_suffix = hashlib.md5(base.encode()).hexdigest()[:8]
    return f"org_{hash_suffix}"
