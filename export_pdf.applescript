-- Export the Group 10 report that sits beside this script.
-- From the repository root: osascript export_pdf.applescript
-- Writes report.pdf in that same directory and overwrites it.
-- Does not use a personal Desktop path. Not executed by the verification pass.

on parentFolder(posixPath)
	set oldDelims to AppleScript's text item delimiters
	set AppleScript's text item delimiters to "/"
	set parts to text items of posixPath
	if (count of parts) > 0 then set item -1 of parts to ""
	set folderPath to parts as text
	set AppleScript's text item delimiters to oldDelims
	return folderPath
end parentFolder

set projectDir to parentFolder(POSIX path of (path to me))
set docPath to POSIX file (projectDir & "AILT9019_Final_Report_Group10.docx")
set pdfPath to projectDir & "report.pdf"
tell application "Microsoft Word"
	activate
	open docPath
	save as active document filename pdfPath file format format PDF
	close active document saving no
end tell
