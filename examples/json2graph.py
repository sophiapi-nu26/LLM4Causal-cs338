import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

def json_to_graphml(input_file: str, output_file: str) -> None:
    """
    Convert a JSON file with relationships to a GraphML file.

    The JSON file should contain a list of relationships, each with a subject, object,
    and relationship. Subjects and objects have a name and type. The output GraphML
    file will have nodes for subjects and objects (with name as ID and type as an attribute)
    and directed edges with the relationship as an attribute.

    Args:
        input_file (str): Path to the input JSON file.
        output_file (str): Path to the output GraphML file.

    Raises:
        FileNotFoundError: If the input JSON file is not found.
        json.JSONDecodeError: If the JSON file is invalid.
        KeyError: If the JSON structure is missing required keys.
    """
    # Read the JSON file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Input file '{input_file}' not found.")
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in '{input_file}': {str(e)}", e.doc, e.pos)

    # Create the GraphML root element
    graphml = ET.Element('graphml', xmlns="http://graphml.graphdrawing.org/xmlns")
    graphml.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    graphml.set('xsi:schemaLocation', 'http://graphml.graphdrawing.org/xmlns http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd')

    # Define keys for node and edge attributes
    ET.SubElement(graphml, 'key', id='d0', **{'for': 'node'}, **{'attr.name': 'type'}, **{'attr.type': 'string'})
    ET.SubElement(graphml, 'key', id='d1', **{'for': 'edge'}, **{'attr.name': 'relationship'}, **{'attr.type': 'string'})

    # Create the graph element (directed)
    graph = ET.SubElement(graphml, 'graph', id='G', edgedefault='directed')

    # Track unique nodes to avoid duplicates
    nodes = {}

    # Process each relationship
    for rel in data:
        try:
            subject = rel['subject']
            object_ = rel['object']
            relationship = rel['relationship']
            subject_name = subject['name']
            subject_type = subject['type']
            object_name = object_['name']
            object_type = object_['type']
        except KeyError as e:
            raise KeyError(f"Missing key in JSON relationship: {str(e)}")

        # Add subject node if not already added
        if subject_name not in nodes:
            node = ET.SubElement(graph, 'node', id=subject_name)
            data_type = ET.SubElement(node, 'data', key='d0')
            data_type.text = subject_type
            nodes[subject_name] = subject_type

        # Add object node if not already added
        if object_name not in nodes:
            node = ET.SubElement(graph, 'node', id=object_name)
            data_type = ET.SubElement(node, 'data', key='d0')
            data_type.text = object_type
            nodes[object_name] = object_type

        # Add directed edge
        edge = ET.SubElement(graph, 'edge', source=subject_name, target=object_name)
        data_rel = ET.SubElement(edge, 'data', key='d1')
        data_rel.text = relationship

    # Convert to pretty-printed XML
    rough_string = ET.tostring(graphml, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")

    # Write to GraphML file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)

if __name__ == "__main__":
    try:
        json_to_graphml('relationships.json', 'output.graphml')
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"Error: {str(e)}")