if exists('g:loaded_snips_plugin')
  finish
endif

let g:loaded_snips_plugin = 1

function! s:err(msg)
  echohl Error
  echo a:msg
  echohl NONE
endfunction


function! s:enable()
  call snips#import()

  " unmap unexpected select mode mappings.
  sunmap m
  sunmap <S-M>
  sunmap v

  call s:disable()
endfunction


function! s:disable()
  augroup completor_snips
    autocmd!
  augroup END
endfunction


augroup completor_snips
  autocmd!
  autocmd InsertEnter * call s:enable()
augroup END

let g:snips_snippets_dirs = get(g:, 'snips_snippets_dirs', [])
