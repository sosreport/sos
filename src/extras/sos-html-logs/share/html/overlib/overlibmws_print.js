/*
 overlibmws_print.js plug-in module - Copyright Foteos Macrides 2002-2007. All rights reserved.
   For support of the PRINT feature.
   Initial: April 25, 2005 - Last Revised: January 1, 2007
 See the Change History and Command Reference for overlibmws via:

	http://www.macridesweb.com/oltest/

 Published under an open source license: http://www.macridesweb.com/oltest/license.html
*/

OLloaded=0;
var OLprintCmds='print,printbutton,noautoprint,printcolor,printfont,printsize,printtext,'
+'printbuttontext,printtitle,printfontclass,printcssfile,printxml,printdoctype,printroot,'
+'printtype,printcharset,printurl,printjob',OLprJob=null;OLregCmds(OLprintCmds);

// DEFAULT CONFIGURATION
if(OLud('print'))var ol_print=0;
if(OLud('printbutton'))var ol_printbutton=0;
if(OLud('noautoprint'))var ol_noautoprint=0;
if(OLud('printcolor'))var ol_printcolor="#eeeeff";
if(OLud('printfont'))var ol_printfont="Verdana,Arial,Helvetica";
if(OLud('printsize'))var ol_printsize=1;
if(OLud('printtext'))var ol_printtext='Print';
if(OLud('printbuttontext'))var ol_printbuttontext='Print';
if(OLud('printtitle'))var ol_printtitle="Click to Print";
if(OLud('printfontclass'))var ol_printfontclass="";
if(OLud('printcssfile'))var ol_printcssfile="";
if(OLud('printxml'))var ol_printxml="";
if(OLud('printdoctype'))var ol_printdoctype=
 '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" '
+'"http://www.w3.org/TR/html4/loose.dtd">';
if(OLud('printroot'))var ol_printroot="<html>";
if(OLud('printtype'))var ol_printtype="text/html";
if(OLud('printcharset'))var ol_printcharset="iso-8859-1";
if(OLud('printurl'))var ol_printurl="";
if(OLud('printjob'))var ol_printjob="";
// END CONFIGURATION

var o3_print=0,o3_printbutton=0,o3_noautoprint,o3_printcolor="",o3_printfont="",o3_printsize=1,
o3_printtext="",o3_printbuttontext="",o3_printtitle="",o3_printfontclass="",o3_printcssfile="",
o3_printxml="",o3_printdoctype="",o3_printroot="",o3_printtype="",o3_printcharset="",
o3_printurl="",o3_printjob="";

function OLloadPrint(){
OLload(OLprintCmds);
}

function OLparsePrint(pf,i,ar){
var k=i,t=OLtoggle,q=OLparQuo;
if(k<ar.length){
if(Math.abs(ar[k])==PRINT){t(ar[k],pf+'print');return k;}
if(Math.abs(ar[k])==PRINTBUTTON){t(ar[k],pf+'printbutton');return k;}
if(Math.abs(ar[k])==NOAUTOPRINT){t(ar[k],pf+'noautoprint');return k;}
if(ar[k]==PRINTCOLOR){q(ar[++k],pf+'printcolor');return k;}
if(ar[k]==PRINTFONT){q(ar[++k],pf+'printfont');return k;}
if(ar[k]==PRINTSIZE){q(ar[++k],pf+'printsize');return k;}
if(ar[k]==PRINTTEXT){q(ar[++k],pf+'printtext');return k;}
if(ar[k]==PRINTBUTTONTEXT){q(ar[++k],pf+'printbuttontext');return k;}
if(ar[k]==PRINTTITLE){q(ar[++k],pf+'printtitle');return k;}
if(ar[k]==PRINTFONTCLASS){q(ar[++k],pf+'printfontclass');return k;}
if(ar[k]==PRINTCSSFILE){q(ar[++k],pf+'printcssfile');return k;}
if(ar[k]==PRINTXML){q(ar[++k],pf+'printxml');return k;}
if(ar[k]==PRINTDOCTYPE){q(ar[++k],pf+'printdoctype');return k;}
if(ar[k]==PRINTROOT){q(ar[++k],pf+'printroot');return k;}
if(ar[k]==PRINTTYPE){q(ar[++k],pf+'printtype');return k;}
if(ar[k]==PRINTCHARSET){q(ar[++k],pf+'printcharset');return k;}
if(ar[k]==PRINTURL){q(ar[++k],pf+'printurl');return k;}
if(ar[k]==PRINTJOB){q(ar[++k],pf+'printjob');return k;}}
return -1;
}

function OLprintDims(){
if(OLhasDims(o3_printsize)){if(OLns4)o3_printsize="2";}else
if(!OLns4){var i=parseInt(o3_printsize);o3_printsize=(i>0&&i<8)?OLpct[i]:OLpct[0];}
}

function OLchkPrint(){if(!o3_sticky)o3_print=0;else over.print=null;}

function OLprintCapLGF(){
var n=(OLovertwoPI&&over2&&over==over2)?2:1;
return(o3_print&&!o3_printbutton?'<td align="right"><a href="javascript:'+OLfnRef
+'return OLprint('+n+');" '+(o3_printtitle?'title="'+o3_printtitle+'" ':'')+'onclick="'
+OLfnRef+'return OLprint('+n+');"'+(o3_printfontclass?' class="'+o3_printfontclass+'">':
(OLns4?'><':'')+OLlgfUtil(0,1,'','a',o3_printcolor,o3_printfont,o3_printsize))+o3_printtext
+(o3_printfontclass?'':(OLns4?OLlgfUtil(1,1,'','a'):''))+'</a></td>':'');
}

function OLprintFgLGF(){
var n=(OLovertwoPI&&over2&&over==over2)?2:1;return (o3_print&&(!o3_cap||o3_printbutton)?
'<div align="center"><form action="javascript:void(0);"><input type="button" '
+(OLns4?'':'style="font-family:Verdana;font-size:11px;color:#000000;" ')+'value="'
+o3_printbuttontext+'" title="'+o3_printtitle+'" '+(OLgek?'autocomplete="off" ':'')
+'onclick="'+OLfnRef+'return OLprint('+n+');" /></form></div>':'');
}

function OLprint(n){
if(n!=2&&OLovertwoPI&&over2&&over==over2)cClick2();
if(!(over&&over.print))return false;if(o3_printjob){eval(o3_printjob);return false;}
if(o3_printurl){if(!window.print||o3_noautoprint)
alert('Print (Control-P) the OLprint Window when it appears, then close it.');OLprJob=
window.open(o3_printurl,'OLurlJob','resizable=1,status=1,screenX=0,left=0,screenY=0,top=0');
OLprJob.focus();if(OLprJob){if(window.print&&!o3_noautoprint){OLprJob.print();
setTimeout("OLprJob.close();OLprJob=null;",2);}}return false;}
var sx=(OLshadowPI&&o3_shadow?o3_shadowx:0),sy=(OLshadowPI&&o3_shadow?o3_shadowy:0),
lm=20+(sx<0?Math.abs(sx):0),rm=20+(sx>0?sx:0),tm=20+(sy<0?Math.abs(sy):0),bm=20+(sy>0?sy:0),
pWd=o3_width,pHt=(OLns4?over.clip.height:over.offsetHeight),iWd=pWd+lm+rm,iHt=pHt+tm+bm,
fs=(OLfilterPI&&OLie55&&o3_filter?o3_filtershadow:0),Fn='{return false;}',
o2=(OLovertwoPI?OLp1or2c+','+OLp1or2co+','+OLp1co+',scroll,function':'');
t=o3_printxml+o3_printdoctype+o3_printroot+'<head><meta http-equiv="content-Type" content="'
+o3_printtype+'; charset='+o3_printcharset+'" /><title>OLprint Job</title>'
+(o3_printcssfile?'<link rel="stylesheet" type="text/css" href="'+o3_printcssfile+'" />':'')
+'<script type="text/javascript">var OLfnRef="",OLna='+o3_noautoprint+',OLo2="'+o2+'";'
+'function OLprintAndClose(){if(window.print&&!OLna){self.print();setTimeout("self.close()",2);}'
+'else{alert("Print (Control-P) the OLprint Window, then close it.");}}'
+'function OLprint(){if(window.print)self.print();}function cClick(){self.close();}'
+'function nd()'+Fn+'function overlib2()'+Fn+'function nd2()'+Fn+'if(OLo2){'
+'var i,m=OLo2.split(",");for(i=0;i<m.length;i++)eval(m[i].toUpperCase()+"="+0);}</script>'
+'</head><body onLoad="self.focus();OLprintAndClose()">'
+(sx||sy?'<div id="printBackdrop" style="position:absolute;z-index:999;visibility:visible;'
+'width:'+o3_width+(OLns4?';':'px;')+'height:'+pHt+(OLns4?';':'px;')
+(o3_shadowimage?'background-image:url('+o3_shadowimage+');':'background-color:'
+o3_shadowcolor+';')+'left:'+(lm+sx).toString()+(OLns4?';':'px;')+'top:'+(tm+sy).toString()
+(OLns4?';':'px;')+'"></div>':'')
+'<div id="overPrintDiv" style="position:absolute;z-index:1000;visibility:visible;width:'
+o3_width+(OLns4?';':'px;')+(o3_background?'background-image:url('+o3_background+');':'')
+'left:'+lm.toString()+(OLns4?';':'px;')+'top:'+tm.toString()+(OLns4?';':'px;')
+(fs?'filter:progid:DXImageTransform.Microsoft.':'')
+(fs==2?'Shadow(color=\''+o3_filtershadowcolor+'\',direction=135,strength=5);':'')
+(fs==1?'Dropshadow(color=\''+o3_filtershadowcolor+'\');':'')+'">'+over.print
+'</div></body></html>';
OLprJob=window.open('','OLprintJob','resizable=0,width='+iWd+',height='+iHt
+',status=0,location=0,toolbar=0,menubar=0,scrolling=0,screenX=0,left=0,screenY=0,top=0');
OLprJob.document.write(t);OLprJob.document.close();return false;
}

OLregRunTimeFunc(OLloadPrint);
OLregCmdLineFunc(OLparsePrint);

OLprintPI=1;
OLloaded=1;
