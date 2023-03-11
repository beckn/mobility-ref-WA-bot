
import importlib

def get_resource_string(custcode, flow, text, lang):
     module = importlib.import_module("customer.%s.resource.constants_%s" % (custcode, lang))
     res_dict = getattr(module, flow)
     return res_dict.get(text, None)
