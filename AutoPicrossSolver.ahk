^j::

; Take a screenshot of the Picross Touch window and save it as image.png
CaptureScreen()

; Run main.py to collect puzzle data from image
RunWait cmd.exe /c "python main.py",,Hide
FileDelete image.png

; Read and then delete contents from puzzle_values.txt
FileRead, Contents, puzzle_values.txt
values := StrSplit(Contents, ",")
start_x := values[1]
start_y := values[2]
pixel_width := values[3]
puzzle_size := values[4]
FileDelete puzzle_values.txt

; Run nonogram-solver using generated input.json file and generate output file
RunWait cmd.exe /c "npx nonogram-solver input.json",,Hide
FileDelete input.json

; Read contents from nonogram-solver's generated file
FileRead, Contents, output/input.svg
FileRemoveDir output, 1
FoundPos := InStr(Contents, "<use xlink")
Cut := SubStr(Contents, FoundPos)

; Loop through contents and generate an array of hits and misses
arr := []
CutLen := StrLen(Cut)
i := 1
While (i < CutLen - 1) {
	mark := SubStr(Cut, i, 2)
	if (mark = "#h") {
		arr.push(1)
		i := i + 50
	} else if (mark = "#m") {
		arr.push(0)
		i := i + 50
	}
	i := i + 1
}

; Using arr and puzzle values, automatically fill in the puzzle
x := start_x
y := start_y
hit_count := 0
i := 1
Loop, %puzzle_size% {
	Loop, %puzzle_size% {
		if (arr[i]) {
			hit_count := hit_count + 1
		} 
		if (not arr[i] or Mod(i, puzzle_size) = 0) {
			if (hit_count > 0) {
				MouseMove, x, y
				Send, {LButton down}
				Sleep, 25
				loop_count := hit_count - 1
				Loop, %loop_count% {
					x := x + pixel_width
					MouseMove, x, y, 0
				}
				Send, {LButton up}
				hit_count := 0
				x := x + pixel_width
			}
			x := x + pixel_width
		}
		if (Mod(i, puzzle_size) = 0) {
			x := start_x
			y := y + pixel_width
		}
		i := i + 1
	}
}

return

; Functions for taking a screenshot
CaptureScreen(sFile = "image.png", nQuality = "")
{
	WinGetPos, nL, nT, nW, nH, A

	mDC := DllCall("CreateCompatibleDC", "ptr", 0, "ptr")
	hBM := CreateDIBSection(mDC, nW, nH)
	oBM := DllCall("SelectObject", "ptr", mDC, "ptr", hBM, "ptr")
	hDC := DllCall("GetDC", "ptr", 0, "ptr")
	DllCall("BitBlt", "ptr", mDC, "int", 0, "int", 0, "int", nW, "int", nH, "ptr", hDC, "int", nL, "int", nT, "Uint", 0x40CC0020)
	DllCall("ReleaseDC", "ptr", 0, "ptr", hDC)
	DllCall("SelectObject", "ptr", mDC, "ptr", oBM)
	DllCall("DeleteDC", "ptr", mDC)
	Convert(hBM, sFile, nQuality), DllCall("DeleteObject", "ptr", hBM)
}

Convert(sFileFr = "", sFileTo = "", nQuality = "")
{
	SplitPath, sFileTo, , sDirTo, sExtTo, sNameTo
	DllCall("LoadLibrary", "str", "gdiplus.dll", "ptr")
	VarSetCapacity(si, 16, 0), si := Chr(1)
	DllCall("gdiplus\GdiplusStartup", "UintP", pToken, "ptr", &si, "ptr", 0)
	DllCall("gdiplus\GdipCreateBitmapFromHBITMAP", "ptr", sFileFr, "ptr", 0, "ptr*", pImage)
	DllCall("gdiplus\GdipGetImageEncodersSize", "UintP", nCount, "UintP", nSize)
	VarSetCapacity(ci,nSize,0)
	DllCall("gdiplus\GdipGetImageEncoders", "Uint", nCount, "Uint", nSize, "ptr", &ci)
	struct_size := 48+7*A_PtrSize, offset := 32 + 3*A_PtrSize, pCodec := &ci - struct_size
	Loop, %	nCount
		If InStr(StrGet(Numget(offset + (pCodec+=struct_size)), "utf-16") , "." . sExtTo)
			break

	DllCall("gdiplus\GdipSaveImageToFile", "ptr", pImage, "wstr", sFileTo, "ptr", pCodec, "ptr", pParam)
	DllCall("gdiplus\GdiplusShutdown" , "Uint", pToken)
	DllCall("FreeLibrary", "ptr", hGdiPlus)
}

CreateDIBSection(hDC, nW, nH, bpp = 32, ByRef pBits = "")
{
	VarSetCapacity(bi, 40, 0)
	NumPut(40, bi, "uint")
	NumPut(nW, bi, 4, "int")
	NumPut(nH, bi, 8, "int")
	NumPut(bpp, NumPut(1, bi, 12, "UShort"), 0, "Ushort")
	Return DllCall("gdi32\CreateDIBSection", "ptr", hDC, "ptr", &bi, "Uint", 0, "UintP", pBits, "ptr", 0, "Uint", 0, "ptr")
}