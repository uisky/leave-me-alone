(function() {
    var $options = $('#form-options'), $ul = $('ul.tasks-list'),
        $form_edit = $('#form-edit'), $modal_edit = $('#modal-edit'),
        selected = null, task;
    var STATUS_MEANINGS = {
        'open': 'todo',
        'progress': 'в работе',
        'pause': 'пауза',
        'review': 'проверка',
        'done': 'готово',
        'canceled': 'отменено'
    }

    function renderTaskLI(task) {
        var $deadline, $users, $subj, $description, $a;

        $li = $('<li>').attr('data-id', task.id).addClass('li-' + task.status);
        if(selected == task.id) {
            $li.addClass('active')
        }
        if(task.assignee && task.assignee.id == current_user.id) {
            $li.addClass('my')
        }

        $deadline = $('<div class="deadline">');
        var now = new Date();
        if(task.deadline) {
            $deadline
                .append(sprintf('%02d.%02d', task.deadline.getDate(), task.deadline.getMonth() + 1))
                .attr('title', task.deadline.toLocaleString('ru'));
            if(task.status in {'open':1, 'progress':1, 'pause':1} && task.deadline <= now) {
                $deadline.addClass('late');
            }
        }

        $users = $('<div class="users">');
        if(task.assignee) {
            $a = $('<a>').attr('href', 'members/' + task.assignee.id + '/').html(task.assignee.name)
            $users.append($a);
        }

        $subj = $('<div class="subj">');
        $subj.append('<small>[' + task.status + ',' + task.importance + ']</small> ');
        $subj.append($('<strong>').append(task.subject));
        if(task.importance in IMPORTANCE) $subj.append(IMPORTANCE[task.importance].icon);
        if(task.character in CHARACTERS) $subj.append(CHARACTERS[task.character].icon)

        $subj.append(' <a href="#" class="action-edit" title="Редактировать"><i class="fa fa-pencil-square-o"></i></a>');

        $li.append($deadline).append($users).append($subj);

        if(task.description) {
            $description = $('<div class="description">').html(task.description_md);
            $li.append($description)
        }

        return $li;
    }

    function sanitizeTask(task) {
        task.created = new Date(task.created);
        if(task.deadline != null) task.deadline = new Date(task.deadline);
    }

    // Возвращает индекс задачи с заданным id в Tasks или -1, если нихуя не нашло
    function findTaskIndex(id) {
        for(var i = 0; i < Tasks.length; i++) {
            if(Tasks[i].id == id) return i;
        }
        return -1;
    }

    // Рендер списка
    function renderList() {
        $ul.empty();
        for(var i = 0; i < Tasks.length; i++) {
            task = Tasks[i];
            sanitizeTask(task);
            $li = renderTaskLI(task);
            $ul.append($li);
        }
    }

    // jquery.forms callback для редактирования задачи
    function taskSaveCallback(data) {
        if(data.errors) {
            alert(data.errors);
            return;
        }

        sanitizeTask(data);
        Tasks[findTaskIndex(data.id)] = data;
        $ul.find('[data-id=' + data.id + ']').replaceWith(renderTaskLI(data));

        $modal_edit.modal('hide');
    }

    // jquery.forms callback для добавления задачи
    function taskAddCallback(data) {
        if(data.errors) {
            alert(data.errors);
            return;
        }

        sanitizeTask(data);
        Tasks.push(data);
        renderList();

        $modal_edit.modal('hide');
    }

    function taskDeleteHandler(e) {
        if(!confirm('Серьёзно?')) return;
        var id = $(this).data('id')
        $.ajax({
            url: '/projects/' + project.id + '/' + id + '/delete/',
            type: 'POST',
            dataType: 'json',
            data: {ajax: 1},
            success: function(data) {
                i = findTaskIndex(data.id);
                $ul.find('[data-id=' + data.id + ']').remove();
                Tasks.splice(i, 1);
                $modal_edit.modal('hide');
            }
        });
    }

    // События в списке
    $ul.on('click', '.action-edit', function(e) {
        e.preventDefault();
        var id = $(this).parents('li').data('id'), task = Tasks[findTaskIndex(id)];

        $modal_edit.find('.modal-header h4').html('Свойства задачи');

        $form_edit.attr('action', '/projects/' + project.id + '/' + id + '/edit/')
        $form_edit.find('.edit-owner').html(task.user.name);
        $form_edit.find('.edit-status').html('<label class="label status-' + task.status + '">' + STATUS_MEANINGS[task.status] + '</label>');
        $form_edit.find('[name=subject]').val(task.subject);
        $form_edit.find('[name=description]').val(task.description);
        $form_edit.find('[name=deadline]').data('DateTimePicker').date(task.deadline);
        $form_edit.find('[name=importance]').val(task.importance);
        if(task.assignee) {
            $form_edit.find('[name=assigned_id]').val(task.assignee.id);
        }

        $form_edit.ajaxForm({
            success: taskSaveCallback,
            dataType: 'json',
            data: {'ajax': 1}
        });

        $form_edit.find('.action-delete').data('id', id).show();

        $modal_edit.modal('show');
    });

    // Добавить задачу
    $('#btn-task-new').click(function(e) {
        $modal_edit.find('.modal-header h4').html('Добавить задачу');

        $form_edit.attr('action', '/projects/' + project.id + '/subtask/');

        $form_edit.find('.edit-owner').html(current_user.name);
        $form_edit.find('.edit-status').html('<label class="label status-open">' + STATUS_MEANINGS['open'] + '</label>');
        $form_edit.find('[name=subject]').val('').focus();
        $form_edit.find('[name=description]').val('');
        $form_edit.find('[name=deadline]').data('DateTimePicker').date(null);
        $form_edit.find('[name=importance]').val('');
        $form_edit.find('[name=assigned_id]').val('');

        $form_edit.find('.action-delete').hide();

        $form_edit.ajaxForm({
            success: taskAddCallback,
            dataType: 'json',
            data: {'ajax': 1}
        });

        $modal_edit.modal('show');
    });

    $modal_edit.on('shown.bs.modal', function() {
        $form_edit.find('[name=subject]').focus();
    });

    $form_edit.find('.action-delete').click(taskDeleteHandler);

    renderList();
})();
