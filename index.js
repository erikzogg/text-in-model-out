import './frontend/src/css/_custom.scss';
import '@fontsource/ibm-plex-sans/400.css';
import '@fontsource/ibm-plex-sans/500.css';
import 'bpmn-js/dist/assets/diagram-js.css'
import 'bpmn-js/dist/assets/bpmn-font/css/bpmn.css'
import './frontend/src/css/app.css'

import './frontend/src/img/app-logo.svg'
import './frontend/src/img/favicon.png'

import 'bootstrap'
import BpmnJS from 'bpmn-js/lib/Modeler';
import CliModule from 'bpmn-js-cli';
import './frontend/src/js/app.js'

let modeler = new BpmnJS({
    container: '#process-model',
    additionalModules: [
        CliModule
    ],
    cli: {
        bindTo: 'cli'
    }
});

window.modeler = modeler;
