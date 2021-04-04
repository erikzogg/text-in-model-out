document.addEventListener('DOMContentLoaded', function () {
    initApp();
});

let initApp = function () {
    let processDescriptionElement = document.getElementById('process-description');

    processDescriptionElement.addEventListener('input', function (event) {
        let processDescriptionText = event.target.value;

        if (processDescriptionText.trim().length > 0) {
            document.getElementById('button-create-model').removeAttribute('disabled');
        } else {
            document.getElementById('button-create-model').setAttribute('disabled', 'disabled');
        }
    });
};
