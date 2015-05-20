(function() {
    $('#btn-task-delete').click(function() {
        if(!confirm('Вы уверены? Будут удалены все подзадачи!')) return;
        $('#form-delete').submit()
    });

    $('#tabs-task').find('a[href=#task-subtask]').on('shown.bs.tab', function() {
        console.log('FOCUS!');
        $('#form-subtask').find('input[name=subject]').focus();
    });

})();