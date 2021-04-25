function home_setup() {
    $('#searchButtonId').on('click', function () {
        let request = $('#requestInputId').val();
        window.location.replace(`${window.location.origin}/?request=${encodeURIComponent(request)}`);
    });
}
