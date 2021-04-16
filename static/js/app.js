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
        let parentElement = elementRegistry.get(element.actor.replace(/\s/g, ''));
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
        }
    });

    modeler.get('canvas').zoom('fit-viewport');

    const result = await modeler.saveXML();
    const {xml} = result;
};
