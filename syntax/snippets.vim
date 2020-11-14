if exists("b:current_syntax")
  finish
endif

func s:init()
  call snips#import()
  call snips#syntax#define_props()
  call snips#syntax#hi()
endfunc

call s:init()

let b:current_syntax = "snippets"
