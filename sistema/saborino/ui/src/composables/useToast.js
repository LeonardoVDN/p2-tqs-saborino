import { reactive } from 'vue'

const state = reactive({ msg: '', visible: false })
let timer = null

export function useToast() {
  function toast(msg) {
    state.msg = msg
    state.visible = true
    clearTimeout(timer)
    timer = setTimeout(() => { state.visible = false }, 2600)
  }
  return { state, toast }
}
