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
        formData.append('process_description', document.getElementById('process-description').value);

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
            .then(html => {
                handleResponse(html);

                document.getElementById('export-bpmn').removeAttribute('disabled');
                document.getElementById('export-svg').removeAttribute('disabled');
                document.getElementById('clear-process-model').removeAttribute('disabled');
            })
            .catch(error => {
                this.innerHTML = 'Create Process Model';
                this.removeAttribute('disabled');

                console.log(error);
            });
    });

    let clearProcessModel = document.getElementById('clear-process-model');
    clearProcessModel.addEventListener('click', function () {
        modeler.clear();

        document.getElementById('export-bpmn').setAttribute('disabled', 'disabled');
        document.getElementById('export-svg').setAttribute('disabled', 'disabled');
        document.getElementById('clear-process-model').setAttribute('disabled', 'disabled');
    });

    let exportBpmnButton = document.getElementById('export-bpmn');
    exportBpmnButton.addEventListener('click', async function () {
        const result = await modeler.saveXML();
        const {xml} = result;

        downloadFile('Business_Process.bpmn', xml);
    });

    let exportSvgButton = document.getElementById('export-svg');
    exportSvgButton.addEventListener('click', async function () {
        const result = await modeler.saveSVG();
        const {svg} = result;

        downloadFile('Business_Process.svg', svg);
    });

    document.querySelectorAll('.btn-example').forEach(item => {
        item.addEventListener('click', function () {
            let exampleNumber = this.getAttribute('data-btn');

            fetch('/static/examples/process_' + exampleNumber + '.txt')
                .then(response => response.text())
                .then(data => {
                    document.getElementById('process-description').value = data.trim();
                    checkProcessDescription(data);
                });
        });
    });
};

let downloadFile = function (filename, text) {
    let element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
    element.setAttribute('download', filename);

    element.style.display = 'none';
    document.body.appendChild(element);

    element.click();

    document.body.removeChild(element);
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

    modeler.clear();
    await modeler.createDiagram();

    var canvas = modeler.get('canvas');
    var elementFactory = modeler.get('elementFactory');
    var elementRegistry = modeler.get('elementRegistry');
    var modeling = modeler.get('modeling');

    cli.removeShape(modeler.get('elementRegistry').get('StartEvent_1'));

    const participant = elementFactory.createParticipantShape();
    cli.setLabel(participant, 'Organisation');

    modeling.createShape(participant, {x: 300, y: 125}, elementRegistry.get('Process_1'));
    modeling.splitLane(participant, Object.keys(actors).length);

    const lanes = participant.children;

    let lanesPosition = [];

    actors.forEach(function (actor, i) {
        lanesPosition[actor.replace(/\s/g, '')] = i;
        modeling.updateProperties(lanes[i], {id: actor.replace(/\s/g, ''), name: actor});
    });

    elements.forEach(function (element, index) {
        let bpmnElement = modeling.createShape(
            {type: element.type},
            {x: 150 * index, y: lanesPosition[element.actor.replace(/\s/g, '')] * 200},
            participant
        );
        modeling.updateProperties(bpmnElement, {id: element.id, name: element.value});

        if (element.predecessor != null) {
            cli.connect(
                element.predecessor,
                element.id,
                'bpmn:SequenceFlow'
            );
        } else if (element.predecessors != null) {
            element.predecessors.forEach(function (predecessor) {
                cli.connect(
                    predecessor,
                    element.id,
                    'bpmn:SequenceFlow'
                );
            });
        }
    });

    cli.elements().forEach(function (element) {
        if (cli.element(element).type === 'bpmn:ExclusiveGateway' || cli.element(element).type === 'bpmn:ParallelGateway') {
            cli.element(element).outgoing.forEach(function (outgoing, index) {
                if (index > 0) {
                    cli.move(outgoing.target.id, {x: -150, y: index * 150});

                    let predecessors = [];

                    cli.element(outgoing.target.id).outgoing.forEach(function (entry) {
                        predecessors.push(entry);
                    });

                    while (predecessors.length > 0) {
                        let predecessor = predecessors[0];

                        if (predecessor.type !== 'bpmn:SequenceFlow') {
                            cli.move(predecessor.id, {x: -150, y: 0});

                            cli.element(predecessor.id).outgoing.forEach(function (entry) {
                                predecessors.push(entry);
                            });
                        } else {
                            if (!predecessors.includes(cli.element(predecessor.id).target)) {
                                predecessors.push(cli.element(predecessor.id).target);
                            }
                        }

                        predecessors.splice(0, 1);
                    }
                }
            });

            if (cli.element(element).type === 'bpmn:ExclusiveGateway') {
                if (cli.element(element).outgoing.length === 2) {
                    modeling.updateProperties(cli.element(element).outgoing[0], {name: 'Yes'});
                    modeling.updateProperties(cli.element(element).outgoing[1], {name: 'No'});
                }
            }
        }

        if (cli.element(element).type === 'bpmn:Lane') {
            modeling.resizeLane(cli.element(element), {x: cli.element(element).x, y: cli.element(element).y, height: 200, width: cli.element(element).width});
        }
    });

    modeler.get('canvas').zoom('fit-viewport');
};
