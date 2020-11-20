if exists("b:current_syntax")
  finish
endif

if !exists("s:_init")
  let s:_init = 0
endif

func s:init()
  if !s:_init
    call snips#import()
    call snips#syntax#define_props()
    let s:_init = 1
  endif
  call snips#syntax#hi()
endfunc

call s:init()

let b:current_syntax = "snippets"
