^j::

; Run main.py to screenshot and solve puzzle
RunWait cmd.exe /c "python main.py",,Hide

; Read and then delete contents from puzzle_values.txt
FileRead, Contents, puzzle_values.txt
values := StrSplit(Contents, ",")
start_x := values[1]
start_y := values[2]
pixel_width := values[3]
puzzle_size := values[4]
FileDelete puzzle_values.txt

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
				Sleep, 22
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