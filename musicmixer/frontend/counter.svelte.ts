// counter.svelte.ts
//
// The one thing under test: does state declared here, at
// module level, survive a component that imports it being
// destroyed and recreated? If Gradio only recreates the
// component instance and doesn't re-import this module,
// the count should keep climbing across remounts. If Gradio
// somehow reloads the module too, the count would reset to
// 0 each time - and that would be worth knowing before any
// more code is built on the assumption that it doesn't.

export const counter = $state({
	value: 0,
	mounts: 0
});

export function increment(): void {
	counter.value += 1;
}
