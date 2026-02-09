#!/bin/sh
python -c "
import sys
sys.path.insert(0, 'knowledge_graph')
from contact_research_agent import ContactResearchAgent
import inspect
print(inspect.getfile(ContactResearchAgent))
"
