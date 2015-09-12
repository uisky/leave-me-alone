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
        var $deadline, $users, $subj, $status, $more, $description, $a;
        var STATUS_BUTTONS = {
            'open':     '<button class="btn btn-xs" title="Начать заново"><i class="fa fa-refresh"></i></button>',
            'progress': '<button class="btn btn-xs" title="Начать выполнение"><i class="fa fa-play"></i></button>',
            'pause':    '<button class="btn btn-xs" title="Поставить на паузу"><i class="fa fa-pause"></i></button>',
            'review':   '<button class="btn btn-xs" title="Отправить на проверку"><i class="fa fa-eye"></i></button>',
            'done':     '<button class="btn btn-xs" title="Готово"><i class="fa fa-check"></i></button>',
            'canceled': '<button class="btn btn-xs" title="Отменить"><i class="fa fa-close"></i></button>'
        }
        /*
        Элемента списка DOM родной. Схема структуры.
        li[data-id].li-{{status}}.my
            .deadline
            .users
            .subj
                .status
                strong
                span.importance
                span.character
            .more
                button.edit
                .description
                .debug
        */
        // li
        $li = $('<li>').attr('data-id', task.id).addClass('li-' + task.status);
        if(selected == task.id) {
            $li.addClass('active')
        }
        if(task.assignee && task.assignee.id == current_user.id) {
            $li.addClass('my')
        }

        // .deadline
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

        // .users
        $users = $('<div class="users">');
        if(task.assignee) {
            $a = $('<a>').attr('href', 'members/' + task.assignee.id + '/').html(task.assignee.name)
            $users.append($a);
        }

        // .subj
        function makeStatusButton(status, current_status) {
            return $(STATUS_BUTTONS[status]).data('set-status', status).addClass('action-status status-' + current_status);
        }
        $subj = $('<div class="subj">');
        if(task.allowed_statuses.length) {
            $subj.append(makeStatusButton(task.allowed_statuses[0], task.status))
        }

        $subj.append($('<strong>').append(task.subject));
        if(task.importance in IMPORTANCE) $subj.append(IMPORTANCE[task.importance].icon);
        if(task.character in CHARACTERS) $subj.append(CHARACTERS[task.character].icon)

        // .more
        $more = $('<div class="more">');
        // .more .description
        if(task.description) {
            $description = $('<div class="description">').html(task.description_md);
            $more.append($description)
        }

        // .more .info
        var $info = $('<div class="info">');
        $info.append(sprintf('Поставлено: %s %s Статус: %s', task.created.toLocaleString(), task.user.name, task.status));
        $more.append($info);

        // .more .actions
        var $actions = $('<div class="actions">');
        if(task.allowed_statuses.length > 1) {
            for(i = 1; i < task.allowed_statuses.length; i++) {
                $actions.append(makeStatusButton(task.allowed_statuses[i], task.allowed_statuses[i])/* .append('ТАЙТЛ СТАТУСА') */)
            }
        }
        if(current_user.id == task.user.id) {
            $actions.append('<a href="#" class="action-edit btn btn-xs btn-warning pull-right"><i class="fa fa-pencil-square-o"></i> Редактировать</a>');
        }
        if($actions.children().length) $more.append($actions);

        // Собираем всё говно в кучу, уиии!
        $li.append($deadline).append($users).append($subj).append($more);

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

    // Сортировка списка
    function sortTasks() {
        // created, deadline, importance, custom
        var sortby = $options.find('[name=sort]').val();
        function createSorter(param) {
            if(param == 'custom') {
                return function(a, b) {
                    return a.mp[0] - b.mp[0];
                }
            } else {
                return function(a, b) {
                    return b[param] - a[param]
                }
            }
        }
        Tasks.sort(createSorter(sortby));
        console.log('Sort by %s', sortby);
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

        sortTasks();
        renderList();

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

        sortTasks();
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
    $ul
    .on('click', '.subj strong', function(e) {
        console.log('Click on subj');
        killSelection();
        $(this).parents('li').find('.more').toggle();
    }).on('dblclick', '.subj strong', function(e) {
        console.log('DblClick on subj');
        killSelection();
    }).on('click', '.action-edit', function(e) {
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
    }).on('click', 'button.action-status', function(e) {
        var $this = $(this), $li = $this.parents('li'),
            status = $this.data('set-status'), id = $li.data('id');
        console.log('Set status %s to id %d', status, id);
        $.post(
            '/projects/' + project.id + '/' + id + '/status/',
            {status: status, ajax: 1},
            function(data) {
                if(data.errors) {
                    alert(data.errors);
                    return;
                }
                sanitizeTask(data);
                Tasks[findTaskIndex(data.id)] = data;
                $ul.find('[data-id=' + data.id + ']').replaceWith(renderTaskLI(data));
            }
        )
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

    $options.find('[name=sort]').change(function() {
        sortTasks();
        renderList();
    });

    sortTasks();
    renderList();
})();
