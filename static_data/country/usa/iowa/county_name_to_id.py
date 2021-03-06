#				    <option value="00">Select County</option><option value="1">ADAIR</option><option value="2">ADAMS</option><option value="3">ALLAMAKEE</option><option value="4">APPANOOSE</option><option value="5">AUDUBON </option><option value="6">BENTON</option><option value="7">BLACK HAWK</option><option value="8">BOONE</option><option value="9">BREMER </option><option value="10">BUCHANAN</option><option value="11">BUENA VISTA</option><option value="12">BUTLER</option><option value="13">CALHOUN</option><option value="14">CARROLL</option><option value="15">CASS</option><option value="16">CEDAR</option><option value="17">CERRO GORDO</option><option value="18">CHEROKEE</option><option value="19">CHICKASAW</option><option value="20">CLARKE</option><option value="21">CLAY</option><option value="22">CLAYTON</option><option value="23">CLINTON</option><option value="24">CRAWFORD</option><option value="25">DALLAS</option><option value="26">DAVIS</option><option value="27">DECATUR</option><option value="28">DELAWARE</option><option value="29">DES MOINES</option><option value="30">DICKINSON</option><option value="31">DUBUQUE</option><option value="32">EMMET</option><option value="33">FAYETTE</option><option value="34">FLOYD</option><option value="35">FRANKLIN</option><option value="36">FREMONT</option><option value="37">GREENE</option><option value="38">GRUNDY</option><option value="39">GUTHRIE</option><option value="40">HAMILTON</option><option value="41">HANCOCK</option><option value="42">HARDIN</option><option value="43">HARRISON</option><option value="44">HENRY</option><option value="45">HOWARD</option><option value="46">HUMBOLDT</option><option value="47">IDA</option><option value="48">IOWA</option><option value="49">JACKSON</option><option value="50">JASPER</option><option value="51">JEFFERSON</option><option value="52">JOHNSON</option><option value="53">JONES</option><option value="54">KEOKUK</option><option value="55">KOSSUTH</option><option value="56">LEE</option><option value="57">LINN</option><option value="58">LOUISA</option><option value="59">LUCAS</option><option value="60">LYON</option><option value="61">MADISON</option><option value="62">MAHASKA</option><option value="63">MARION</option><option value="64">MARSHALL</option><option value="65">MILLS</option><option value="66">MITCHELL</option><option value="67">MONONA</option><option value="68">MONROE</option><option value="69">MONTGOMERY</option><option value="70">MUSCATINE</option><option value="71">O'BRIEN</option><option value="72">OSCEOLA</option><option value="73">PAGE</option><option value="74">PALO ALTO</option><option value="75">PLYMOUTH</option><option value="76">POCAHONTAS</option><option value="77">POLK</option><option value="78">POTTAWATTAMIE</option><option value="79">POWESHIEK</option><option value="80">RINGGOLD</option><option value="81">SAC</option><option value="82">SCOTT</option><option value="83">SHELBY</option><option value="84">SIOUX</option><option value="85">STORY</option><option value="86">TAMA</option><option value="87">TAYLOR</option><option value="88">UNION</option><option value="89">VAN BUREN</option><option value="90">WAPELLO</option><option value="91">WARREN</option><option value="92">WASHINGTON</option><option value="93">WAYNE</option><option value="94">WEBSTER</option><option value="95">WINNEBAGO</option><option value="96">WINNESHIEK</option><option value="97">WOODBURY</option><option value="98">WORTH</option><option value="99">WRIGHT</option>	
# s/.*?<option value="(\d+)">([^<]+)/"$2":$1,\n/g

county_name_to_id = {
"adair":1,
"adams":2,
"allamakee":3,
"appanoose":4,
"audubon ":5,
"benton":6,
"black hawk":7,
"boone":8,
"bremer ":9,
"buchanan":10,
"buena vista":11,
"butler":12,
"calhoun":13,
"carroll":14,
"cass":15,
"cedar":16,
"cerro gordo":17,
"cherokee":18,
"chickasaw":19,
"clarke":20,
"clay":21,
"clayton":22,
"clinton":23,
"crawford":24,
"dallas":25,
"davis":26,
"decatur":27,
"delaware":28,
"des moines":29,
"dickinson":30,
"dubuque":31,
"emmet":32,
"fayette":33,
"floyd":34,
"franklin":35,
"fremont":36,
"greene":37,
"grundy":38,
"guthrie":39,
"hamilton":40,
"hancock":41,
"hardin":42,
"harrison":43,
"henry":44,
"howard":45,
"humboldt":46,
"ida":47,
"iowa":48,
"jackson":49,
"jasper":50,
"jefferson":51,
"johnson":52,
"jones":53,
"keokuk":54,
"kossuth":55,
"lee":56,
"linn":57,
"louisa":58,
"lucas":59,
"lyon":60,
"madison":61,
"mahaska":62,
"marion":63,
"marshall":64,
"mills":65,
"mitchell":66,
"monona":67,
"monroe":68,
"montgomery":69,
"muscatine":70,
"o'brien":71,
"osceola":72,
"page":73,
"palo alto":74,
"plymouth":75,
"pocahontas":76,
"polk":77,
"pottawattamie":78,
"poweshiek":79,
"ringgold":80,
"sac":81,
"scott":82,
"shelby":83,
"sioux":84,
"story":85,
"tama":86,
"taylor":87,
"union":88,
"van buren":89,
"wapello":90,
"warren":91,
"washington":92,
"wayne":93,
"webster":94,
"winnebago":95,
"winneshiek":96,
"woodbury":97,
"worth":98,
"wright":99,
}
