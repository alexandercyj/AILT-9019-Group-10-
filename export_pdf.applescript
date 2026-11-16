set docPath to POSIX file "/Users/chenxianliang1/Desktop/大二上/AILT9019/AILT-9019-Group-10-/AILT9019_Final_Report_Group10.docx"
set pdfPath to "/Users/chenxianliang1/Desktop/大二上/AILT9019/AILT-9019-Group-10-/report.pdf"
tell application "Microsoft Word"
	activate
	open docPath
	save as active document filename pdfPath file format format PDF
	close active document saving no
end tell
