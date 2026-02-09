#!/bin/sh
cd knowledge_graph
python -c "
from contact_research_agent import ContactResearchAgent
agent = ContactResearchAgent()
result = agent.research_contact({'name': 'ALISON KLEIN', 'title': 'Contracting Officer', 'agency': 'VA'}, force_refresh=True)
print(result)
agent.close()
"
