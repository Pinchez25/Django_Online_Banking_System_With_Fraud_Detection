
const registerForm = document.getElementById('register-form');
const registerButton = document.getElementById('submit-id-submit')
const csrfToken = document.getElementsByName('csrfmiddlewaretoken')[0].value;

registerButton.addEventListener('click', (e) => {
    e.preventDefault();
    const formData = new FormData(registerForm);
    const data = Object.fromEntries(formData);
    delete data.csrfmiddlewaretoken;
    const jsonData = JSON.stringify(data);
    /*
      {"username":"","email":"","national_id":"","account_type":"","user_type":"","password1":"","password2":""}
    * */
    console.log(jsonData);

    fetch('/accounts/register/ajax/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify(data)
    })
    .then(res => res.json())
    .then(data => {
        console.log(data);
    })
    .catch(err => console.log(err));
})
// SyntaxError: Unexpected token '<', "
// <!DOCTYPE "... is not valid JSON error

