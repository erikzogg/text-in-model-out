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
                document.getElementById('process-model').innerHTML = error;
            });
    })
};

let handleResponse = function (data) {
    document.getElementById('process-model').innerHTML = data;
};
