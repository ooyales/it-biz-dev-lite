#!/usr/bin/env python3
"""
Neo4j Knowledge Graph Client
Handles all database operations for contact knowledge graph
"""

from neo4j import GraphDatabase
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KnowledgeGraphClient:
    """Neo4j knowledge graph client for contact management"""
    
    def __init__(self, uri: str, user: str, password: str):
        """
        Initialize connection to Neo4j
        
        Args:
            uri: Neo4j bolt URI (e.g., "bolt://localhost:7687")
            user: Username (default: "neo4j")
            password: Database password
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password), database="contactsgraphdb")
        logger.info(f"Connected to Neo4j at {uri}")
    
    def close(self):
        """Close database connection"""
        self.driver.close()
        logger.info("Neo4j connection closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    # ========================================================================
    # SCHEMA INITIALIZATION
    # ========================================================================
    
    def initialize_schema(self):
        """Create indexes and constraints for optimal performance"""
        
        logger.info("Initializing graph schema...")
        
        with self.driver.session() as session:
            # Constraints (ensure uniqueness)
            constraints = [
                "CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
                "CREATE CONSTRAINT org_id IF NOT EXISTS FOR (o:Organization) REQUIRE o.id IS UNIQUE",
                "CREATE CONSTRAINT event_id IF NOT EXISTS FOR (e:Event) REQUIRE e.id IS UNIQUE",
                "CREATE CONSTRAINT contract_id IF NOT EXISTS FOR (c:Contract) REQUIRE c.id IS UNIQUE",
                "CREATE CONSTRAINT opportunity_id IF NOT EXISTS FOR (op:Opportunity) REQUIRE op.id IS UNIQUE",
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                    logger.info(f"✓ Created constraint: {constraint.split()[2]}")
                except Exception as e:
                    logger.warning(f"Constraint already exists or error: {e}")
            
            # Indexes (speed up lookups)
            indexes = [
                "CREATE INDEX person_email IF NOT EXISTS FOR (p:Person) ON (p.email)",
                "CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.name)",
                "CREATE INDEX org_name IF NOT EXISTS FOR (o:Organization) ON (o.name)",
                "CREATE INDEX contract_number IF NOT EXISTS FOR (c:Contract) ON (c.contract_number)",
            ]
            
            for index in indexes:
                try:
                    session.run(index)
                    logger.info(f"✓ Created index: {index.split()[2]}")
                except Exception as e:
                    logger.warning(f"Index already exists or error: {e}")
        
        logger.info("Schema initialization complete")
    
    # ========================================================================
    # PERSON OPERATIONS
    # ========================================================================
    
    def create_person(self, person_data: Dict[str, Any]) -> str:
        """
        Create a person node
        
        Args:
            person_data: Dict with keys:
                - id: Unique identifier
                - name: Full name
                - email: Email address (optional)
                - phone: Phone number (optional)
                - title: Current title (optional)
                - organization: Current org (optional)
                - role_type: Decision Maker, Technical Lead, etc.
                - influence_level: Very High, High, Medium, Low
                - And other fields...
        
        Returns:
            Person ID
        """
        with self.driver.session() as session:
            query = """
            MERGE (p:Person {id: $id})
            SET p += $properties,
                p.created_at = COALESCE(p.created_at, datetime()),
                p.updated_at = datetime()
            RETURN p.id as person_id
            """
            
            result = session.run(query, id=person_data['id'], properties=person_data)
            person_id = result.single()['person_id']
            
            logger.info(f"Created/updated person: {person_data.get('name')} ({person_id})")
            return person_id
    
    def get_person(self, person_id: str) -> Optional[Dict]:
        """Get person by ID"""
        with self.driver.session() as session:
            query = "MATCH (p:Person {id: $id}) RETURN p"
            result = session.run(query, id=person_id)
            record = result.single()
            
            if record:
                return dict(record['p'])
            return None
    
    def find_person_by_email(self, email: str) -> Optional[Dict]:
        """Find person by email address"""
        with self.driver.session() as session:
            query = "MATCH (p:Person {email: $email}) RETURN p"
            result = session.run(query, email=email)
            record = result.single()
            
            if record:
                return dict(record['p'])
            return None
    
    def search_people(self, name_query: str) -> List[Dict]:
        """Search people by name (fuzzy)"""
        with self.driver.session(database="contactsgraphdb") as session:
            cypher_query = """
            MATCH (p:Person)
            WHERE toLower(p.name) CONTAINS toLower($search_term)
            RETURN p
            LIMIT 20
            """
            result = session.run(cypher_query, search_term=name_query)
            return [dict(record['p']) for record in result]
    
    # ========================================================================
    # ORGANIZATION OPERATIONS
    # ========================================================================
    
    def create_organization(self, org_data: Dict[str, Any]) -> str:
        """Create an organization node"""
        with self.driver.session() as session:
            query = """
            MERGE (o:Organization {id: $id})
            SET o += $properties,
                o.created_at = COALESCE(o.created_at, datetime()),
                o.updated_at = datetime()
            RETURN o.id as org_id
            """
            
            result = session.run(query, id=org_data['id'], properties=org_data)
            org_id = result.single()['org_id']
            
            logger.info(f"Created/updated organization: {org_data.get('name')} ({org_id})")
            return org_id
    
    def get_organization(self, org_id: str) -> Optional[Dict]:
        """Get organization by ID"""
        with self.driver.session() as session:
            query = "MATCH (o:Organization {id: $id}) RETURN o"
            result = session.run(query, id=org_id)
            record = result.single()
            
            if record:
                return dict(record['o'])
            return None
    
    # ========================================================================
    # RELATIONSHIP OPERATIONS
    # ========================================================================
    
    def create_relationship(
        self, 
        from_id: str, 
        to_id: str, 
        rel_type: str, 
        properties: Dict[str, Any] = None
    ) -> bool:
        """
        Create relationship between nodes
        
        Args:
            from_id: Source node ID
            to_id: Target node ID
            rel_type: WORKS_AT, REPORTS_TO, SPOKE_WITH, etc.
            properties: Relationship properties (date, strength, source, etc.)
        
        Returns:
            Success boolean
        """
        if properties is None:
            properties = {}
        
        # Add metadata
        properties['created_at'] = datetime.now().isoformat()
        
        with self.driver.session(database="contactsgraphdb") as session:
            # Dynamic relationship type requires string manipulation
            query = f"""
            MATCH (from {{id: $from_id}})
            MATCH (to {{id: $to_id}})
            MERGE (from)-[r:{rel_type}]->(to)
            SET r += $properties
            RETURN r
            """
            
            result = session.run(
                query, 
                from_id=from_id, 
                to_id=to_id, 
                properties=properties
            )
            
            if result.single():
                logger.info(f"Created relationship: {from_id} -{rel_type}-> {to_id}")
                return True
            
            return False
    
    def create_works_at(
        self, 
        person_id: str, 
        org_id: str, 
        title: str = None,
        start_date: str = None,
        confidence: float = 1.0,
        source: str = None
    ):
        """Create WORKS_AT relationship"""
        properties = {
            'title': title,
            'start_date': start_date,
            'confidence': confidence,
            'source': source
        }
        return self.create_relationship(person_id, org_id, 'WORKS_AT', properties)
    
    def create_reports_to(
        self,
        person_id: str,
        manager_id: str,
        since: str = None,
        source: str = None
    ):
        """Create REPORTS_TO relationship"""
        properties = {
            'since': since,
            'source': source
        }
        return self.create_relationship(person_id, manager_id, 'REPORTS_TO', properties)
    
    def create_interaction(
        self,
        person1_id: str,
        person2_id: str,
        interaction_type: str,
        date: str,
        outcome: str = None,
        notes: str = None
    ):
        """Create interaction relationship (bidirectional)"""
        properties = {
            'type': interaction_type,
            'date': date,
            'outcome': outcome,
            'notes': notes
        }
        return self.create_relationship(person1_id, person2_id, 'INTERACTED_WITH', properties)
    
    # ========================================================================
    # QUERY OPERATIONS
    # ========================================================================
    
    def get_person_network(self, person_id: str, depth: int = 1) -> Dict:
        """
        Get person's network up to N hops away
        
        Args:
            person_id: Person to center on
            depth: How many hops (1 = direct connections, 2 = friends of friends)
        
        Returns:
            Dict with nodes and edges
        """
        with self.driver.session() as session:
            query = f"""
            MATCH (p:Person {{id: $person_id}})
            CALL apoc.path.subgraphAll(p, {{
                relationshipFilter: '<>',
                minLevel: 1,
                maxLevel: {depth}
            }})
            YIELD nodes, relationships
            RETURN nodes, relationships
            """
            
            # Fallback if APOC not installed
            fallback_query = f"""
            MATCH path = (p:Person {{id: $person_id}})-[*1..{depth}]-(other)
            WITH COLLECT(DISTINCT p) + COLLECT(DISTINCT other) as nodes,
                 COLLECT(DISTINCT relationships(path)) as rels
            RETURN nodes, rels as relationships
            """
            
            try:
                result = session.run(query, person_id=person_id)
            except:
                logger.warning("APOC not available, using fallback query")
                result = session.run(fallback_query, person_id=person_id)
            
            record = result.single()
            
            if not record:
                return {'nodes': [], 'edges': []}
            
            nodes = [dict(node) for node in record['nodes']]
            edges = []
            
            for rel_list in record['relationships']:
                if isinstance(rel_list, list):
                    for rel in rel_list:
                        edges.append({
                            'from': rel.start_node['id'],
                            'to': rel.end_node['id'],
                            'type': rel.type,
                            'properties': dict(rel)
                        })
                else:
                    edges.append({
                        'from': rel_list.start_node['id'],
                        'to': rel_list.end_node['id'],
                        'type': rel_list.type,
                        'properties': dict(rel_list)
                    })
            
            return {'nodes': nodes, 'edges': edges}
    
    def find_shortest_path(self, person1_id: str, person2_id: str) -> List[Dict]:
        """
        Find shortest path between two people
        
        Returns:
            List of nodes and relationships in path
        """
        with self.driver.session() as session:
            query = """
            MATCH (p1:Person {id: $person1_id}), (p2:Person {id: $person2_id})
            MATCH path = shortestPath((p1)-[*..5]-(p2))
            RETURN path
            """
            
            result = session.run(query, person1_id=person1_id, person2_id=person2_id)
            record = result.single()
            
            if not record:
                return []
            
            path = record['path']
            path_data = []
            
            for node in path.nodes:
                path_data.append({'type': 'node', 'data': dict(node)})
            
            for rel in path.relationships:
                path_data.append({'type': 'relationship', 'data': dict(rel)})
            
            return path_data
    
    def get_decision_makers_at_agency(self, agency_name: str) -> List[Dict]:
        """Get all decision makers at specific agency"""
        with self.driver.session() as session:
            query = """
            MATCH (p:Person)-[:WORKS_AT]->(o:Organization)
            WHERE o.name CONTAINS $agency 
              AND p.role_type = 'Decision Maker'
            RETURN p, o
            ORDER BY p.influence_level DESC
            """
            
            result = session.run(query, agency=agency_name)
            
            return [
                {
                    'person': dict(record['p']),
                    'organization': dict(record['o'])
                }
                for record in result
            ]
    
    def get_network_statistics(self) -> Dict:
        """Get overall network statistics"""
        with self.driver.session() as session:
            query = """
            MATCH (p:Person) WITH count(p) as person_count
            MATCH (o:Organization) WITH person_count, count(o) as org_count
            MATCH ()-[r]->() WITH person_count, org_count, count(r) as rel_count
            MATCH (p:Person {role_type: 'Decision Maker'}) 
            WITH person_count, org_count, rel_count, count(p) as dm_count
            RETURN person_count, org_count, rel_count, dm_count
            """
            
            result = session.run(query)
            record = result.single()
            
            if record:
                return {
                    'total_people': record['person_count'],
                    'total_organizations': record['org_count'],
                    'total_relationships': record['rel_count'],
                    'decision_makers': record['dm_count']
                }
            
            return {}
    
    # ========================================================================
    # BULK OPERATIONS
    # ========================================================================
    
    def bulk_create_people(self, people: List[Dict]) -> int:
        """Create multiple people at once"""
        count = 0
        
        with self.driver.session() as session:
            for person in people:
                try:
                    self.create_person(person)
                    count += 1
                except Exception as e:
                    logger.error(f"Error creating person {person.get('name')}: {e}")
        
        logger.info(f"Bulk created {count}/{len(people)} people")
        return count
    
    def clear_database(self):
        """⚠️  WARNING: Delete all nodes and relationships"""
        logger.warning("Clearing entire database...")
        
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        
        logger.warning("Database cleared!")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def generate_person_id(name: str, email: str = None) -> str:
    """Generate unique person ID"""
    import hashlib
    
    if email:
        base = email.lower()
    else:
        base = name.lower().replace(' ', '_')
    
    hash_suffix = hashlib.md5(base.encode()).hexdigest()[:8]
    return f"person_{hash_suffix}"


def generate_org_id(org_name: str) -> str:
    """Generate unique organization ID"""
    import hashlib
    
    base = org_name.lower().replace(' ', '_')
    hash_suffix = hashlib.md5(base.encode()).hexdigest()[:8]
    return f"org_{hash_suffix}"


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Configuration
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "your_password"  # Change this!
    
    # Initialize client
    with KnowledgeGraphClient(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD) as kg:
        # Initialize schema
        kg.initialize_schema()
        
        # Create a test person
        person_id = generate_person_id("Sarah Johnson", "sarah.j@disa.mil")
        kg.create_person({
            'id': person_id,
            'name': 'Sarah Johnson',
            'email': 'sarah.j@disa.mil',
            'title': 'Contracting Officer',
            'role_type': 'Decision Maker',
            'influence_level': 'Very High',
            'phone': '(703) 555-0123'
        })
        
        # Create organization
        org_id = generate_org_id("Defense Information Systems Agency")
        kg.create_organization({
            'id': org_id,
            'name': 'Defense Information Systems Agency',
            'abbreviation': 'DISA',
            'type': 'Federal Agency',
            'parent': 'Department of Defense'
        })
        
        # Create relationship
        kg.create_works_at(
            person_id=person_id,
            org_id=org_id,
            title="Contracting Officer",
            start_date="2020-01-01",
            source="LinkedIn"
        )
        
        # Get statistics
        stats = kg.get_network_statistics()
        print("\nNetwork Statistics:")
        print(f"  People: {stats.get('total_people', 0)}")
        print(f"  Organizations: {stats.get('total_organizations', 0)}")
        print(f"  Relationships: {stats.get('total_relationships', 0)}")
        print(f"  Decision Makers: {stats.get('decision_makers', 0)}")
        
        print("\n✓ Knowledge graph client working!")
