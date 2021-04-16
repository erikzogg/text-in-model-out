const defaultXml = `<?xml version="1.0" encoding="UTF-8"?>
                    <bpmn:definitions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" id="Definitions_1" targetNamespace="http://bpmn.io/schema/bpmn">
                        <bpmn:process id="BPMNProcess_1" isExecutable="false"/>
                        <bpmndi:BPMNDiagram id="BPMNDiagram_1">
                            <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="BPMNProcess_1"/>
                        </bpmndi:BPMNDiagram>
                    </bpmn:definitions>`

document.addEventListener('DOMContentLoaded', function () {
    initApp();
});

let initApp = function () {
    let processDescriptionElement = document.getElementById('process-description');

    processDescriptionElement.addEventListener('input', function (event) {
        checkProcessDescription(event.target.value);
    });

    let buttonCreateModel = document.getElementById('button-create-model');

    buttonCreateModel.addEventListener('click', function () {
        this.setAttribute('disabled', 'disabled');
        this.innerHTML = 'Please wait...';

        let formData = new FormData();
        formData.append('text', document.getElementById('process-description').value);

        const request = new Request('/api', {
            headers: {'X-CSRFToken': document.getElementById('csrf_token').value},
            method: 'POST',
            body: formData
        });

        fetch(request)
            .then()
            .then(response => {
                this.innerHTML = 'Create Process Model';
                this.removeAttribute('disabled');

                if (!response.ok) {
                    throw Error(response.statusText);
                }

                return response.text();
            })
            .then(html => handleResponse(html))
            .catch(error => {
                this.innerHTML = 'Create Process Model';
                this.removeAttribute('disabled');

                document.getElementById('process-model').innerHTML = error;
            });
    });

    document.querySelectorAll('.btn-example').forEach(item => {
        item.addEventListener('click', function () {
            let exampleNumber = this.getAttribute('data-btn');

            fetch('/static/examples/process_' + exampleNumber + '.txt')
                .then(response => response.text())
                .then(data => {
                    document.getElementById('process-description').value = data;
                    checkProcessDescription(data);
                });
        });
    });
};

let checkProcessDescription = function (text) {
    if (text.trim().length > 0) {
        document.getElementById('button-create-model').removeAttribute('disabled');
    } else {
        document.getElementById('button-create-model').setAttribute('disabled', 'disabled');
    }
};

let handleResponse = async function (data) {
    let elements = JSON.parse(data);

    let actors = [];

    elements.forEach(function (element) {
        if (!actors.includes(element.actor)) {
            actors.push(element.actor);
        }
    });

    await modeler.createDiagram();

    var canvas = modeler.get('canvas');
    var elementFactory = modeler.get('elementFactory');
    var elementRegistry = modeler.get('elementRegistry');
    var modeling = modeler.get('modeling');

    cli.removeShape(modeler.get('elementRegistry').get('StartEvent_1'));

    const participant = elementFactory.createParticipantShape();
    cli.setLabel(participant, 'Organisation');

    modeling.createShape(participant, {x: 0, y: 0}, elementRegistry.get('Process_1'));
    modeling.splitLane(participant, Object.keys(actors).length);

    const lanes = participant.children;

    let laneReferences = [];

    actors.forEach(function (actor, i) {
        laneReferences[actor] = lanes[i];
        modeling.updateProperties(lanes[i], {name: actor, id: actor.replace(/\s/g, '')});
    });

    elements.forEach(function (element, index) {
        switch (element.type) {
            case 'bpmn:Task':
                break;
            case 'bpmn:StartEvent':
                let startEvent = cli.append(elementRegistry.get(element.actor.replace(/\s/g, '')), 'bpmn:StartEvent');
                cli.setLabel(startEvent, element.value);
                break;
            default:
                break;
        }
    });

    modeler.get('canvas').zoom('fit-viewport');

    const result = await modeler.saveXML();
    const {xml} = result;
    console.log(xml);
};
