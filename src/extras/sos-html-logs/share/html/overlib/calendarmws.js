/*
 calendermws.js - Script for generating calender popups and selecting dates for form
  submissions.  See http://www.macridesweb.com/oltest/calendarmws.html for a demonstration.
  Initial: November 9, 2003 - Last Revised: November 23, 2006 

****
 Original:  Kedar R. Bhave (softricks@hotmail.com)
 Web Site:  http://www.softricks.com
 (uses window popups)

 Modifications and customizations to work with the overLIB v3.50
 Author:   James B. O'Connor (joconnor@nordenterprises.com)
 Web Site: http://www.nordenterprises.com
 Developed for use with http://home-owners-assoc.com
 Note: while overlib works fine with Netscape 4, this function does not work very
    well, since portions of the "over" div end up under other fields on the form and
    cannot be seen.  If you want to use this with NS4,  you'll need to change the
    positioning in the overlib() call to make sure the "over" div gets positioned
    away from all other form fields
 The O'Connor script and many more are available free online at:
    The JavaScript Source!! http://javascript.internet.com

 Further modifications made by Foteos Macrides (http://www.macridesweb.com/oltest/)
    and Bill McCormick (wpmccormick@freeshell.org) for overlibmws
*/

var ggPosX = -1;
var ggPosY = -1;
var ggInactive = 0;
var ggOnChange = null;

var ggWinContent = "";

var weekend = [0,6];
var weekendColor = "#e0e0e0";
var fontface = "Verdana";
var fontsize = 8; // in "pt" units; used with "font-size" style element

var gNow = new Date();

Calendar.Months = ["January", "February", "March", "April", "May", "June",
"July", "August", "September", "October", "November", "December"];

// Non-Leap year Month days..
Calendar.DOMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
// Leap year Month days..
Calendar.lDOMonth = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

function Calendar(p_item, p_month, p_year, p_format) {
	if ((p_month == null) && (p_year == null)) return;

	if (p_month == null) {
		this.gMonthName = null;
		this.gMonth = null;
		this.gYearly = true;
	} else {
		this.gMonthName = Calendar.get_month(p_month);
		this.gMonth = new Number(p_month);
		this.gYearly = false;
	}

	this.gYear = p_year;
	this.gFormat = p_format;
	this.gBGColor = "white";
	this.gFGColor = "black";
	this.gTextColor = "black";
	this.gHeaderColor = "black";
	this.gReturnItem = p_item;
}

Calendar.get_month = Calendar_get_month;
Calendar.get_daysofmonth = Calendar_get_daysofmonth;
Calendar.calc_month_year = Calendar_calc_month_year;

function Calendar_get_month(monthNo) {
	return Calendar.Months[monthNo];
}

function Calendar_get_daysofmonth(monthNo, p_year) {
	/* 
	Check for leap year ..
	1.Years evenly divisible by four are normally leap years, except for... 
	2.Years also evenly divisible by 100 are not leap years, except for... 
	3.Years also evenly divisible by 400 are leap years. 
	*/
	if ((p_year % 4) == 0) {
		if ((p_year % 100) == 0 && (p_year % 400) != 0)
			return Calendar.DOMonth[monthNo];
	
		return Calendar.lDOMonth[monthNo];
	} else
		return Calendar.DOMonth[monthNo];
}

function Calendar_calc_month_year(p_Month, p_Year, incr) {
	/* 
	Will return an 1-D array with 1st element being the calculated month 
	and second being the calculated year 
	after applying the month increment/decrement as specified by 'incr' parameter.
	'incr' will normally have 1/-1 to navigate thru the months.
	*/
	var ret_arr = new Array();
	
	if (incr == -1) {
		// B A C K W A R D
		if (p_Month == 0) {
			ret_arr[0] = 11;
			ret_arr[1] = parseInt(p_Year) - 1;
		} else {
			ret_arr[0] = parseInt(p_Month) - 1;
			ret_arr[1] = parseInt(p_Year);
		}
	} else if (incr == 1) {
		// F O R W A R D
		if (p_Month == 11) {
			ret_arr[0] = 0;
			ret_arr[1] = parseInt(p_Year) + 1;
		} else {
			ret_arr[0] = parseInt(p_Month) + 1;
			ret_arr[1] = parseInt(p_Year);
		}
	}
	return ret_arr;
}

function Calendar_calc_month_year(p_Month, p_Year, incr) {
	/* 
	Will return an 1-D array with 1st element being the calculated month 
	and second being the calculated year 
	after applying the month increment/decrement as specified by 'incr' parameter.
	'incr' will normally have 1/-1 to navigate thru the months.
	*/
	var ret_arr = new Array();
	
	if (incr == -1) {
		// B A C K W A R D
		if (p_Month == 0) {
			ret_arr[0] = 11;
			ret_arr[1] = parseInt(p_Year) - 1;
		} else {
			ret_arr[0] = parseInt(p_Month) - 1;
			ret_arr[1] = parseInt(p_Year);
		}
	} else if (incr == 1) {
		// F O R W A R D
		if (p_Month == 11) {
			ret_arr[0] = 0;
			ret_arr[1] = parseInt(p_Year) + 1;
		} else {
			ret_arr[0] = parseInt(p_Month) + 1;
			ret_arr[1] = parseInt(p_Year);
		}
	}
	return ret_arr;
}

// This is for compatibility with Navigator 3, we have to create and discard one object
// before the prototype object exists.
new Calendar();

Calendar.prototype.getMonthlyCalendarCode = function() {
	var vCode = "";
	var vHeader_Code = "";
	var vData_Code = "";
	
	// Begin Table Drawing code here..
	vCode += ('<div align="center"><table border="1" bgcolor="' + this.gBGColor +
	 "\" style='font-size:" + fontsize + "pt;'>");

	vHeader_Code = this.cal_header();
	vData_Code = this.cal_data();
	vCode += (vHeader_Code + vData_Code);

	vCode += '</table></div>';

	return vCode;
}

Calendar.prototype.show = function() {
	var vCode = "";

	var vDate = new Date();
	vDate.setMonth(this.gMonth);
	vDate.setFullYear(this.gYear);
	var vNowMonth = gNow.getMonth();
	var vNowYear = gNow.getFullYear();
	var yOK=!ggInactive||vNowYear<vDate.getFullYear()?1:0;
	var mOK=!ggInactive||(yOK||
        (vNowYear<=vDate.getFullYear()&&vNowMonth<vDate.getMonth()))?1:0;

	// build content into global var ggWinContent
	ggWinContent += ('<div style="font-family:\'' + fontface + '\';font-weight:bold;'
		+'font-size:' + fontsize + 'pt;text-align:center;">');
	ggWinContent += (this.gMonthName + ' ' + this.gYear);
	ggWinContent += '</div>';
	
	// Show navigation buttons
	var prevMMYYYY = Calendar.calc_month_year(this.gMonth, this.gYear, -1);
	var prevMM = prevMMYYYY[0];
	var prevYYYY = prevMMYYYY[1];

	var nextMMYYYY = Calendar.calc_month_year(this.gMonth, this.gYear, 1);
	var nextMM = nextMMYYYY[0];
	var nextYYYY = nextMMYYYY[1];
	
	ggWinContent += ('<table width="100%" border="1" cellspacing="0" cellpadding="0" '
		+'bgcolor="#e0e0e0" style="font-size:' + fontsize
		+'pt;"><tr><td align="center">');
	ggWinContent += ('['
		+(yOK?'<a href="javascript:void(0);" '
		+'title="Go back one year" '
		+'onmouseover="window.status=\'Go back one year\'; return true;" '
		+'onmouseout="window.status=\'\'; return true;" '
		+'onclick="Build(\'' + this.gReturnItem + '\', \'' + this.gMonth + '\', \''
		+(parseInt(this.gYear)-1) + '\', \'' + this.gFormat + '\');"'
		+'>':'')
		+'&lt;&lt;Year'
		+(yOK?'</a>':'')
		+']</td><td align="center">');
	ggWinContent += ('['
		+(mOK?'<a href="javascript:void(0);" '
		+'title="Go back one month" '
		+'onmouseover="window.status=\'Go back one month\'; return true;" '
		+'onmouseout="window.status=\'\'; return true;" '
		+'onclick="Build(\'' + this.gReturnItem + '\', \'' + prevMM + '\', \''
		+prevYYYY + '\', \'' + this.gFormat + '\');"'
		+'>':'')
		+'&lt;Mon'
		+(mOK?'</a>':'')
		+']</td><td align="center">');
	ggWinContent += '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td align="center">';
	ggWinContent += ('[<a href="javascript:void(0);" '
		+'title="Go forward one month" '
		+'onmouseover="window.status=\'Go forward one month\'; return true;" '
		+'onmouseput="window.status=\'\'; return true;" '
		+'onclick="Build(\'' + this.gReturnItem + '\', \'' + nextMM + '\', \''
		+nextYYYY + '\', \'' + this.gFormat + '\');"'
		+'>Mon&gt;</a>]</td><td align="center">');
	ggWinContent += ('[<a href="javascript:void(0);" '
		+'title="Go forward one year" '
		+'onmouseover="window.status=\'Go forward one year\'; return true;" '
		+'onmouseout="window.status=\'\'; return true;" '
		+'onClick="Build(\'' + this.gReturnItem + '\', \'' + this.gMonth + '\', \''
		+(parseInt(this.gYear)+1) + '\', \'' + this.gFormat + '\');"'
		+'>Year&gt;&gt;</a>]</td></tr></table><div style="font-size:3px;">'
		+'&nbsp;</div>');

	// Get the complete calendar code for the month, and add it to the content var
	vCode = this.getMonthlyCalendarCode();
	ggWinContent += vCode;
}

Calendar.prototype.showY = function() {
	var vCode = "";
	var i;

	ggWinContent += ('<div style="font-family:\'' + fontface + '\';font-weight:bold;'
		+'font-size:' + (fontsize+1) +'pt;text-align:center;">' + this.gYear +'</div>');

	var vDate = new Date();
	vDate.setDate(1);
	vDate.setFullYear(this.gYear);
	var vNowYear = gNow.getFullYear();
	var yOK=!ggInactive||vNowYear<vDate.getFullYear()?1:0;

	// Show navigation buttons
	var prevYYYY = parseInt(this.gYear) - 1;
	var nextYYYY = parseInt(this.gYear) + 1;
	
	ggWinContent += ('<table width="100%" border="1" cellspacing="0" cellpadding="0" '
		+'bgcolor="#e0e0e0" style="font-size:' + fontsize + 'pt;"><tr><td '
		+'align="center">');
	ggWinContent += ('['
		+(yOK?'<a href="javascript:void(0);" '
		+'title="Go back one year" '
		+'onmouseover="window.status=\'Go back one year\'; return true;" '
		+'onmouseout="window.status=\'\'; return true;" '
		+'onclick="Build(\'' + this.gReturnItem + '\', null, \'' + prevYYYY + '\', \''
		+this.gFormat + '\');">':'')
		+'&lt;&lt;Year'
		+(yOK?'<a>':'')
		+']</td><td align="center">');
	ggWinContent += '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td align="center">';
	ggWinContent += ('[<a href="javascript:void(0);" '
		+'title="Go forward one year" '
		+'onmouseover="window.status=\'Go forward one year\'; return true;" '
		+'onmouseout="window.status=\'\'; return true;" '
		+'onclick="Build(\'' + this.gReturnItem + '\', null, \'' + nextYYYY + '\', \''
		+this.gFormat + '\');">Year&gt;&gt;</a>]</td></tr></table>');

	// Get the complete calendar code for each month.
	// start a table and first row in the table
	ggWinContent += ('<table width="100%" border="0" cellspacing="0" cellpadding="2" '
		+'style="font-size:' + fontsize + 'pt;"><tr>');
	for (i=0; i<12; i++) {
		// start the table cell
		ggWinContent += '<td align="center" valign="top">';
		this.gMonth = i;
		this.gMonthName = Calendar.get_month(this.gMonth);
		vCode = this.getMonthlyCalendarCode();
		ggWinContent += (this.gMonthName + '/' + this.gYear + '<div '
			+'style="font-size:2px;">&nbsp;</div>');
		ggWinContent += vCode;
		ggWinContent += '</td>';
		if (i == 3 || i == 7) ggWinContent += '</tr><tr>';
	}
	ggWinContent += '</tr></table>';
}

Calendar.prototype.cal_header = function() {
	var vCode = '<tr>';
	vCode += ('<td width="14%" style="font-family:' + fontface + ';color:'
		+this.gHeaderColor + ';font-weight:bold;">Sun</td>');
	vCode += ('<td width="14%" style="font-family:' + fontface + ';color:'
		+this.gHeaderColor + ';font-weight:bold;">Mon</td>');
	vCode += ('<td width="14%" style="font-family:' + fontface + ';color:'
		+this.gHeaderColor + ';font-weight:bold;">Tue</td>');
	vCode += ('<td width="14%" style="font-family:' + fontface + ';color:'
		+this.gHeaderColor + ';font-weight:bold;">Wed</td>');
	vCode += ('<td width="14%" style="font-family:' + fontface + ';color:'
		+this.gHeaderColor + ';font-weight:bold;">Thu</td>');
	vCode += ('<td width="14%" style="font-family:' + fontface + ';color:'
		+this.gHeaderColor + ';font-weight:bold;">Fri</td>');
	vCode += ('<td width="16%" style="font-family:' + fontface + ';color:'
		+this.gHeaderColor + ';font-weight:bold;">Sat</td>');
	vCode += '</tr>';
	return vCode;
}

Calendar.prototype.cal_data = function() {
	var vDate = new Date();
	vDate.setDate(1);
	vDate.setMonth(this.gMonth);
	vDate.setFullYear(this.gYear);

	var vNowDay = gNow.getDate();
	var vNowMonth = gNow.getMonth();
	var vNowYear = gNow.getFullYear();

	var yOK=!ggInactive||vNowYear<=vDate.getFullYear()?1:0;
	var mOK=!ggInactive||vNowYear<vDate.getFullYear()||
	 (vNowYear==vDate.getFullYear()&&vNowMonth<=vDate.getMonth())?1:0;
	var ymOK=yOK&&mOK?1:0;
	var dOK=!ggInactive||vNowYear<vDate.getFullYear()||vNowMonth<vDate.getMonth()?1:0;

	var vFirstDay=vDate.getDay();
	var vDay=1;
	var vLastDay=Calendar.get_daysofmonth(this.gMonth, this.gYear);
	var vOnLastDay=0;
	var vCode = '<tr>';
        var i,j,k,m;
	var orig = eval("document." + this.gReturnItem + ".value").toString();
	/*
	Get day for the 1st of the requested month/year..
	Place as many blank cells before the 1st day of the month as necessary. 
	*/
	for (i=0; i<vFirstDay; i++) { vCode +=
		('<td width="14%"' + this.write_weekend_string(i)
		+'style="font-family:\'' + fontface + '\';text-align:center;">&nbsp;</td>');
	}

	// Write rest of the 1st week
	for (j=vFirstDay; j<7; j++) { vCode +=
		('<td width="14%"' + this.write_weekend_string(j) +'style="font-family:\''
		+ fontface + '\';text-align:center;">'
		+((ymOK)&&(vDay>=vNowDay||dOK)?'<a href="javascript:void(0);" '
		+'title="set date to ' + this.format_data(vDay) + '" '
		+'onmouseover="window.status=\'set date to ' + this.format_data(vDay) + '\'; '
		+'return true;" '
		+'onmouseout="window.status=\'\'; return true;" '
		+'onclick="document.' + this.gReturnItem + '.value=\'' + this.format_data(vDay)
		+'\';ggPosX= -1;ggPosY= -1;' + OLfnRef + 'cClick();'
		+'if((ggOnChange)&&(document.' + this.gReturnItem + '.value!=\'' + orig
		+'\'))ggOnChange();">':'')
		+ this.format_day(vDay)
		+((ymOK)&&(vDay>=vNowDay||dOK)?'</a>':'')
		+'</td>');
		vDay += 1;
	}
	vCode += '</tr>';

	// Write the rest of the weeks
	for (k=2; k<7; k++) {
		vCode += '<tr>';
		for (j=0; j<7; j++) { vCode +=
			('<td width="14%"' + this.write_weekend_string(j)
			+'style="font-family:\'' + fontface + '\';text-align:center;">'
			+((ymOK)&&(vDay>=vNowDay||dOK)?'<a '
			+'href="javascript:void(0);" '
			+'title="set date to ' + this.format_data(vDay) + '" '
			+'onmouseover="window.status=\'set date to ' + this.format_data(vDay)
			+'\'; return true;" '
			+'onmouseout="window.status=\'\'; return true;" '
			+'onclick="document.' + this.gReturnItem + '.value=\''
			+ this.format_data(vDay) + '\';ggPosX= -1;ggPosY= -1;'
			+ OLfnRef + 'cClick();'
			+'if((ggOnChange)&&(document.' + this.gReturnItem + '.value!=\''
			+orig + '\'))ggOnChange();">':'')
			+ this.format_day(vDay)
			+((ymOK)&&(vDay>=vNowDay||dOK)?'</a>':'')
			+'</td>');
			vDay += 1;
			if (vDay > vLastDay) {
				vOnLastDay = 1;
				break;
			}
		}
		if (j == 6) vCode += '</tr>';
		if (vOnLastDay == 1) break;
	}
	
	// Fill up the rest of last week with proper blanks, so that we get proper square blocks
	for (m=1; m<(7-j); m++) { vCode +=
		('<td width="14%"' + this.write_weekend_string(j+m) + 'style="font-family:\''
		+ fontface + '\';color:gray;text-align:center;">&nbsp;</td>');
	}
	return vCode;
}

Calendar.prototype.format_day = function(vday) {
	var vNowDay = gNow.getDate();
	var vNowMonth = gNow.getMonth();
	var vNowYear = gNow.getFullYear();

	if (vday == vNowDay && this.gMonth == vNowMonth && this.gYear == vNowYear)
		return ('<span style="color:red;font-weight:bold;">' + vday + '</span>');
	else
		return (vday);
}

Calendar.prototype.write_weekend_string = function(vday) {
	var i;

	// Return special formatting for the weekend day.
	for (i=0; i<weekend.length; i++) {
		if (vday == weekend[i])
			return (' bgcolor="' + weekendColor + '"');
	}
	
	return "";
}

Calendar.prototype.format_data = function(p_day) {
	var vData;
	var vMonth = 1 + this.gMonth;
	vMonth = (vMonth.toString().length < 2) ? "0" + vMonth : vMonth;
	var vMon = Calendar.get_month(this.gMonth).substr(0,3).toUpperCase();
	var vFMon = Calendar.get_month(this.gMonth).toUpperCase();
	var vY4 = new String(this.gYear);
	var vY2 = new String(this.gYear.substr(2,2));
	var vDD = (p_day.toString().length < 2) ? "0" + p_day : p_day;

	switch (this.gFormat) {
		case "MM\/DD\/YYYY" :
			vData = vMonth + "\/" + vDD + "\/" + vY4;
			break;
		case "MM\/DD\/YY" :
			vData = vMonth + "\/" + vDD + "\/" + vY2;
			break;
		case "MM-DD-YYYY" :
			vData = vMonth + "-" + vDD + "-" + vY4;
			break;
		case "YYYY-MM-DD" :
			vData = vY4 + "-" + vMonth + "-" + vDD;
			break;
		case "MM-DD-YY" :
			vData = vMonth + "-" + vDD + "-" + vY2;
			break;
		case "DD\/MON\/YYYY" :
			vData = vDD + "\/" + vMon + "\/" + vY4;
			break;
		case "DD\/MON\/YY" :
			vData = vDD + "\/" + vMon + "\/" + vY2;
			break;
		case "DD-MON-YYYY" :
			vData = vDD + "-" + vMon + "-" + vY4;
			break;
		case "DD-MON-YY" :
			vData = vDD + "-" + vMon + "-" + vY2;
			break;
		case "DD\/MONTH\/YYYY" :
			vData = vDD + "\/" + vFMon + "\/" + vY4;
			break;
		case "DD\/MONTH\/YY" :
			vData = vDD + "\/" + vFMon + "\/" + vY2;
			break;
		case "DD-MONTH-YYYY" :
			vData = vDD + "-" + vFMon + "-" + vY4;
			break;
		case "DD-MONTH-YY" :
			vData = vDD + "-" + vFMon + "-" + vY2;
			break;
		case "DD\/MM\/YYYY" :
			vData = vDD + "\/" + vMonth + "\/" + vY4;
			break;
		case "DD\/MM\/YY" :
			vData = vDD + "\/" + vMonth + "\/" + vY2;
			break;
		case "DD-MM-YYYY" :
			vData = vDD + "-" + vMonth + "-" + vY4;
			break;
		case "DD-MM-YY" :
			vData = vDD + "-" + vMonth + "-" + vY2;
			break;
		case "DD.MM.YYYY" :
			vData = vDD + "." + vMonth + "." + vY4;
			break;
		case "DD.MM.YY" :
			vData = vDD + "." + vMonth + "." + vY2;
			break;
		default :
			vData = vMonth + "\/" + vDD + "\/" + vY4;
	}

	return vData;
}

function Build(p_item, p_month, p_year, p_format) {
	var gCal = new Calendar(p_item, p_month, p_year, p_format);

	// Customize your Calendar here..
	gCal.gBGColor="white";
	gCal.gLinkColor="black";
	gCal.gTextColor="black";
	gCal.gHeaderColor="darkgreen";

	// initialize the content string
	ggWinContent = "";

	// Check for DRAGGABLE support
	if (typeof ol_draggable == 'undefined') DRAGGABLE = DONOTHING;

	// Choose appropriate show function
	if (gCal.gYearly) {
		// Note: you can set ggPosX and ggPosY as part of the onclick javascript
		// code before you call the show_yearly_calendar function:
		//	onclick="ggPosX=20;ggPosY=5;show_yearly_calendar(...);"
                if (OLns6) {
			if (ggPosX == -1) ggPosX = 20;
			if (ggPosY == -1) ggPosY = 10;
		}
		if (fontsize == 8) fontsize = 6;
		// generate the calendar
		gCal.showY();
	} else {
		if (fontsize == 6) fontsize = 8;
		gCal.show();
	}

	// Clear any previous EXCLUSIVE setting
	o3_exclusive=0;
	// If X and Y positions are not specified use MIDX and RELY
	if (ggPosX == -1 && ggPosY == -1) {
		overlib(ggWinContent, AUTOSTATUSCAP, STICKY, EXCLUSIVE, DRAGGABLE,
		 CLOSECLICK, TEXTSIZE,'8pt', CAPTIONSIZE,'8pt', CLOSESIZE,'8pt',
		 CAPTION,'Select a date', MIDX,0, RELY,10);
        // Otherwise use FIXX and FIXY
	} else {
		// Make sure popup is on screen
		var X = ((ggPosX < 10)?0:ggPosX - 10), Y = ((ggPosY < 10)?0:ggPosY - 10);
		window.scroll(X, Y);
		// Put up the calendar
		overlib(ggWinContent, AUTOSTATUSCAP, STICKY, EXCLUSIVE, DRAGGABLE,
		 CLOSECLICK, TEXTSIZE,'8pt', CAPTIONSIZE,'8pt', CLOSESIZE,'8pt',
		 CAPTION,'Select a date', FIXX,ggPosX, FIXY,ggPosY);
		// Reset the position variables
		ggPosX = -1; ggPosY = -1;
	}
}

function show_calendar() {
	var p_item	// Return Item.
	var p_month	// 0-11 for Jan-Dec; 12 for All Months.
	var p_year	// 4-digit year
	var p_format	// Date format (YYYY-MM-DD, DD/MM/YYYY, ...)
	fontsize = 8;

	p_item = arguments[0];
	if (arguments[1] == "" || arguments[1] == null || arguments[1] == '12')
		p_month = new String(gNow.getMonth());
	else
		p_month = arguments[1];
	if (arguments[2] == "" || arguments[2] == null)
		p_year = new String(gNow.getFullYear().toString());
	else
		p_year = arguments[2];
	if (arguments[3] == "" || arguments[3] == null)
		p_format = "YYYY-MM-DD";
	else
		p_format = arguments[3];

	if (OLns4) return overlib('Sorry, your browser does not support this feature. '
	 +'Manually enter<br>' + p_format,
	 FGCOLOR,'#ffffcc', TEXTSIZE,2, STICKY, NOCLOSE, OFFSETX,-10, OFFSETY,-10,
	 WIDTH,110, BASE,2);

	Build(p_item, p_month, p_year, p_format);
}

function show_yearly_calendar() {
	var p_item	// Return Item.
	var p_year	// 4-digit year
	var p_format	// Date format (YYYY-MM-DD, DD/MM/YYYY, ...)

	p_item = arguments[0];
	if (arguments[1] == "" || arguments[1] == null)
		p_year = new String(gNow.getFullYear().toString());
	else
		p_year = arguments[1];
	if (arguments[2] == "" || arguments[2] == null)
		p_format = "YYYY-MM-DD";
	else
		p_format = arguments[2];

	if (OLns4) return overlib('Sorry, your browser does not support this feature. '
	 +'Manually enter<br>' + p_format,
	 FGCOLOR,'#ffffcc', TEXTSIZE,2, STICKY, NOCLOSE, OFFSETX,-10, OFFSETY,-10,
	 WIDTH,110, BASE,2);

	Build(p_item, null, p_year, p_format);
}
