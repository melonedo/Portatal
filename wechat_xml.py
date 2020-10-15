# Decode and encode as xml
from lxml import etree

def xml_to_dict(xml_str):
    tree = etree.fromstring(xml_str)
    res = {}
    for child in tree:
        res[child.tag] = child.text
    return res

def dict_to_xml(xml_dict):
    tree = etree.Element("xml")
    for k, v in xml_dict.items():
        e = etree.SubElement(tree, k)
        if isinstance(v, int):
            e.text = v
        else:
            e.text = etree.CDATA(v)
    return etree.tostring(tree)
