"""
# To fetch these phone numbers I used the following script.
from county_name_to_id import county_name_to_id 
import requests
import time
import re
print('county_name_to_auditor_phone = {')
obrienyet=False
for county_name in county_name_to_id:
    cn = re.sub(' ','_',county_name)
    if cn.find("'")>-1:
        cn = 'obrien'
        obrienyet = True
    if not(obrienyet):
        continue
    url = requests.get(f'https://iowaauditors.org/{cn}')
    telmatch = re.search(r'\((\d\d\d)\)\s*(\d\d\d)-(\d\d\d\d)',url.content.decode('UTF-8'))
    print(f'"{county_name}":"{telmatch.group(1)}-{telmatch.group(2)}-{telmatch.group(3)}",')
    time.sleep(2)
print('}')

"""


county_name_to_auditor_phone = {
"adair":"641-743-2546",
"adams":"641-322-3340",
"allamakee":"563-568-3522",
"appanoose":"641-856-6191",
"audubon ":"712-563-2584",
"benton":"319-472-2365",
"black hawk":"319-833-3002",
"boone":"515-433-0502",
"bremer ":"319-352-0340",
"buchanan":"319-334-4109",
"buena vista":"712-749-2542",
"butler":"319-267-2670",
"calhoun":"712-297-7741",
"carroll":"712-792-9802",
"cass":"712-243-4570",
"cedar":"563-886-3168",
"cerro gordo":"641-421-3034",
"cherokee":"712-225-6704",
"chickasaw":"641-394-2100",
"clarke":"641-342-3315",
"clay":"712-262-1569",
"clayton":"563-245-1106",
"clinton":"563-244-0568",
"crawford":"712-263-3045",
"dallas":"515-993-6914",
"davis":"641-664-2101",
"decatur":"641-446-4323",
"delaware":"563-927-4701",
"des moines":"319-753-8232",
"dickinson":"712-336-3356",
"dubuque":"563-589-4499",
"emmet":"712-362-4261",
"fayette":"563-422-3497",
"floyd":"641-257-6131",
"franklin":"641-456-5622",
"fremont":"712-374-2031",
"greene":"515-386-5680",
"grundy":"319-824-3122",
"guthrie":"641-747-3619",
"hamilton":"515-832-9510",
"hancock":"641-923-3163",
"hardin":"641-939-8109",
"harrison":"712-644-2401",
"henry":"319-385-0756",
"howard":"563-547-9203",
"humboldt":"515-332-1571",
"ida":"712-364-2626",
"iowa":"319-642-3923",
"jackson":"563-652-3144",
"jasper":"641-792-7016",
"jefferson":"641-472-2840",
"johnson":"319-356-6004",
"jones":"319-462-2282",
"keokuk":"641-622-2320",
"kossuth":"515-295-2718",
"lee":"319-372-3705",
"linn":"319-892-5300",
"louisa":"319-523-3373",
"lucas":"641-774-4512",
"lyon":"712-472-8517",
"madison":"515-462-3914",
"mahaska":"641-673-7148",
"marion":"641-828-2217",
"marshall":"641-754-6323",
"mills":"712-527-3146",
"mitchell":"641-832-3946",
"monona":"712-433-2191",
"monroe":"641-932-2865",
"montgomery":"712-623-5127",
"muscatine":"563-263-5821",
"o'brien":"712-957-3225",
"osceola":"712-754-2241",
"page":"712-542-3219",
"palo alto":"712-852-2924",
"plymouth":"712-546-6100",
"pocahontas":"712-335-3361",
"polk":"515-286-3080",
"pottawattamie":"712-328-5700",
"poweshiek":"641-623-5443",
"ringgold":"641-464-3239",
"sac":"712-662-7310",
"scott":"563-326-8631",
"shelby":"712-755-3831",
"sioux":"712-737-2216",
"story":"515-382-7210",
"tama":"641-484-2740",
"taylor":"712-523-2280",
"union":"641-782-1701",
"van buren":"319-293-3129",
"wapello":"641-683-0020",
"warren":"515-961-1020",
"washington":"319-653-7715",
"wayne":"641-872-2242",
"webster":"515-573-7175",
"winnebago":"641-585-3412",
"winneshiek":"563-382-5085",
"woodbury":"712-279-6465",
"worth":"641-324-2316",
"wright":"515-532-2771",
}

