^j::

; Run nonogram-solver
RunWait cmd.exe /c "npx nonogram-solver input.json",,Hide

; Read contents from nonogram-solver's generated file
FileRead, Contents, output/input.svg
FoundPos := InStr(Contents, "<use xlink")
Cut := SubStr(Contents, FoundPos)

; Loop through contents and solve PicrossTouch puzzle
CutLen := StrLen(Cut)
i := 1
start_x := 724
start_y := 329
pixel_width := 45.9
puzzle_size := 15
x := start_x
y := start_y
While (i < CutLen + 2) {
    if (SubStr(Cut, i, 2) = "#h") {
        MouseMove, x, y
		Send, {LButton down}
		Sleep, 22
		Send, {LButton up}
		i := i + 50
		x := x + pixel_width
    } else if (SubStr(Cut, i, 2) = "#m") {
		i := i + 50
		x := x + pixel_width
    }
	if ((x - start_x) > (puzzle_size * pixel_width)) {
	    x := start_x
		y := y + pixel_width
	}
	i := i + 1
}
return