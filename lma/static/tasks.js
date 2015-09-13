(function() {
    var $tasks = $('.tasks-tree > ul, ul.tasks-list'), $forms = $('#form-subtask, #form-edit');

    // Сабмит редакторов по Ctrl+Enter
    $forms.keypress(function(e) {
        if(e.ctrlKey && e.which == 10) {
            $(this).submit();
        }
    });

    // Показать/скрыть готовое
    function hideDone() {
        if(Cookies.get('hide_done')) {
            $tasks.addClass('hide-done');
            $('#btn-toggle-done').html('<i class="fa fa-eye-slash"></i>').attr('title', 'Показать выполненные задачи');
        } else {
            $tasks.removeClass('hide-done');
            $('#btn-toggle-done').html('<i class="fa fa-eye"></i>').attr('title', 'Скрыть выполненные задачи');;
        }
    }
    $('#btn-toggle-done').click(function() {
        if(Cookies.get('hide_done')) {
            Cookies.remove('hide_done', {path: ''});
        } else {
            Cookies.set('hide_done', 1, {expires: 365, path: ''});
        }
        hideDone();
    });
    hideDone();

})();