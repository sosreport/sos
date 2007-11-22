/*
 BabelFish.js - Script for using the AltaVista BabelFish translation service.
   Adapted by Foteos Macrides for use with the overlibmws code set.
   See http://www.macridesweb.com/oltest/BabelFish.html for a demonstration.
   Initial: October 26, 2003 - Last Revised: April 17, 2004 
*/
OLtrans_en = new Image();
OLtrans_en.src = "http://babelfish.altavista.com/static/i/af/trans_en.gif"
OLtrans_en_off = new Image();
OLtrans_en_off.src = "http://babelfish.altavista.com/static/i/af/trans_en_off.gif"

var OLbfURL = location.href;

if (location.href.indexOf("babelfish.altavista.com") == -1) {
var BabelFish =
'<div class="babelfish">'
+'<p align="center"><strong>Note:</strong> This page can be viewed in a different language by '
+'selecting the corresponding flag below.</p>'
+'<p align="center">'
+'<!--script type="text/javascript" src="http://www.altavista.com/r?entr"></script-->'
+'<Map name="translate_eng">'
+'<AREA COORDS="0,1,129,38" SHAPE="rect" target="translate" '
+'title="Go to Babel Fish home page/" '
+'href="http://babelfish.altavista.com">'
+'<AREA COORDS="5,110,32,126" SHAPE="rect" target="translate" '
+'title="Translate English to Chinese." '
+'href="http://babelfish.altavista.com/babelfish/tr?doit=done&url='+OLbfURL+'&lp=en_zh">'
+'<AREA COORDS="38,110,65,126" SHAPE="rect" target="translate" '
+'title="Translate English to German." '
+'href="http://babelfish.altavista.com/babelfish/tr?doit=done&url='+OLbfURL+'&lp=en_de">'
+'<AREA COORDS="70,110,95,126"  SHAPE="rect" target="translate" '
+'title="Translate English to Japanese." '
+'href="http://babelfish.altavista.com/babelfish/tr?doit=done&url='+OLbfURL+'&lp=en_ja">'
+'<AREA COORDS="99,110,123,126" SHAPE="rect" target="translate" '
+'title="Translate English to Korean." '
+'href="http://babelfish.altavista.com/babelfish/tr?doit=done&url='+OLbfURL+'&lp=en_ko">'
+'<AREA COORDS="8,130,31,146" SHAPE="rect" target="translate" '
+'title="Translate English to French." '
+'href="http://babelfish.altavista.com/babelfish/tr?doit=done&url='+OLbfURL+'&lp=en_fr">'
+'<AREA COORDS="39,130,65,146" SHAPE="rect" target="translate" '
+'title="Translate English to Italian." '
+'href="http://babelfish.altavista.com/babelfish/tr?doit=done&url='+OLbfURL+'&lp=en_it">'
+'<AREA COORDS="70,130,93,146" SHAPE="rect" target="translate" '
+'title="Translate English to Portuguese." '
+'href="http://babelfish.altavista.com/babelfish/tr?doit=done&url='+OLbfURL+'&lp=en_pt">'
+'<AREA COORDS="100,130,125,146" SHAPE="rect" target="translate" '
+'title="Translate English to Spanish." '
+'href="http://babelfish.altavista.com/babelfish/tr?doit=done&url='+OLbfURL+'&lp=en_es">'
+'</Map>'
+'<img src="http://babelfish.altavista.com/static/i/af/trans_en.gif" '
+'width="131" height="156" usemap="#translate_eng" border="0"><br></p>'
+'<p align="center">The translations are done via the AltaVista Babel Fish service.</p></div>';
}else{
var BabelFish =
'<div class="babelfish"><p align="center">'
+'<img src="http://babelfish.altavista.com/static/i/af/trans_en_off.gif" '
+'width="131" height="156" border="0"></p></div>';
}
