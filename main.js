import BpmnJS from 'bpmn-js/lib/Modeler';
import CliModule from 'bpmn-js-cli';

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
