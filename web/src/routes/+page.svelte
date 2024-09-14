<script>
    import * as xterm from '@xterm/xterm';
    import '@xterm/xterm/css/xterm.css';
    import { onMount } from 'svelte';
    import { loadPyodide } from 'pyodide';
    let pyodide;
    async function initPyodide() {
        pyodide = await loadPyodide({
            indexURL : "https://cdn.jsdelivr.net/pyodide/v0.26.2/full/"
        });
        const response = await fetch('/t.zip');
        const buffer = await response.arrayBuffer();
        pyodide.FS.writeFile('t.zip', new Uint8Array(buffer));
        await pyodide.runPythonAsync(`
            import zipfile
            with zipfile.ZipFile('t.zip', 'r') as z:
                z.extractall()
        `);
        console.log('unzipped t.zip');



        await pyodide.loadPackage('micropip');
        const micropip = pyodide.pyimport('micropip');
        await micropip.install('sqlalchemy');

        console.log('Pyodide and micropip is ready');

        runPython();
    }
    async function runPython() {
        if (pyodide) {
            const result = pyodide.runPython(`
            import sqlalchemy
            import calamity_calendar
            cal = calamity_calendar.Calamity()

            import sys
            from js import term

            class TerminalWriter:
                def write(self, text):
                    # replace all newlines with the terminal newline
                    text = text.replace('\\n', '\\r\\n')
                    term.write(text)
                def flush(self):
                    pass

            sys.stdout = TerminalWriter()

            cal.display()
           `);
            console.log("Result of 1+1: ", result);
        }
    }

    let terminalElement;

    const initTerminal = () => {
        window.term = new xterm.Terminal();
        initPyodide();
        window.term.open(terminalElement);
        // set the size of the terminal
        window.term.resize(100, 24);  
        window.term.write('Hello from xterm.js');
        window.term.onKey(e => {
            // window.term.write(e.key);
            pyodide.runPythonAsync(`
                cal.main_loop_callback('${e.key}')
                cal.display()
            `);
        }); 
    };
    onMount(() => {
        initTerminal();
    });
</script>

<button on:click={runPython}>Run Python</button>

<div bind:this={terminalElement}
    autofocus
    class="terminalContainer"
></div>



<h1>Welcome to SvelteKit</h1>
<p>Visit <a href="https://kit.svelte.dev">kit.svelte.dev</a> to read the documentation</p>
test