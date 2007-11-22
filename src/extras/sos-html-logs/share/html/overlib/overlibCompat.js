////////////////////////////////////////////////////////////////////////////////////
// OVERLIB 2 COMPATABILITY FUNCTIONS
// Include this if you are upgrading from overlib v2.x.  Otherwise, forget it.
////////////////////////////////////////////////////////////////////////////////////
// Converts old 0=left, 1=right and 2=center into constants.
function vpos_convert(d){if(d==0){d=LEFT;}else{if(d==1){d=RIGHT;}else{d=CENTER;}}return d;}
// Simple popup
function dts(d,text){o3_hpos=vpos_convert(d);overlib(text,o3_hpos,CAPTION,"");}
// Caption popup
function dtc(d,text,title){o3_hpos=vpos_convert(d);overlib(text,CAPTION,title,o3_hpos);}
// Sticky
function stc(d,text,title){o3_hpos=vpos_convert(d);overlib(text,CAPTION,title,o3_hpos,STICKY);}
// Simple popup right
function drs(text){dts(1,text);}
// Caption popup right
function drc(text,title){dtc(1,text,title);}
// Sticky caption right
function src(text,title){stc(1,text,title);}
// Simple popup left
function dls(text){dts(0,text);}
// Caption popup left
function dlc(text,title){dtc(0,text,title);}
// Sticky caption left
function slc(text,title){stc(0,text,title);}
// Simple popup center
function dcs(text){dts(2,text);}
// Caption popup center
function dcc(text,title){dtc(2,text,title);}
// Sticky caption center
function scc(text,title){stc(2,text,title);}
