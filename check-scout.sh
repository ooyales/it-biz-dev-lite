cd knowledge_graph
python3 << 'EOF'
from graph.neo4j_client import KnowledgeGraphClient
import os

kg = KnowledgeGraphClient(
    uri='bolt://localhost:7687',
    user='neo4j',
    password=os.getenv('NEO4J_PASSWORD')
)

with kg.driver.session(database="contactsgraphdb") as session:
    result = session.run("""
        MATCH (p:Person)-[:WORKS_AT]->(o:Organization)
        RETURN DISTINCT o.name as org
        ORDER BY o.name
        LIMIT 20
    """)
    
    print("Organizations in your graph:")
    for record in result:
        print(f"  - {record['org']}")

kg.close()
EOF
