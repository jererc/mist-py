var showDelays = {};


function toggleElementNew(element, direction, delay) {
    var id = 'new';
    clearTimeout(showDelays[id]);
    var info = $(element).find('.element-new');
    showDelays[id] = setTimeout(function () {
        if (direction == 'up') {
            info.slideUp('slow', function() {
                $(element).removeClass('element-highlight', 200);
            });
        } else {
            info.slideDown('fast', function() {
                $(element).addClass('element-highlight');
            });
        }
    }, delay);
};

function toggleElement(element, direction, delay) {
    var id = $(element).attr('data-id');
    clearTimeout(showDelays[id]);
    var info = $(element).find('.element-info');
    showDelays[id] = setTimeout(function () {
        if (direction == 'up') {
            info.slideUp('slow');
        } else {
            info.slideDown('fast');
        }
    }, delay);
};

function initBaseActions() {
    $('.content-new').mouseenter(function() {
        $(this).addClass('element-highlight');
        toggleElementNew(this, 'down', 600);
    });
    $('.content-new').mouseleave(function() {
        toggleElementNew(this, 'up', 600);
    });
    $('.content-element').mouseenter(function() {
        $(this).addClass('element-highlight');
        toggleElement(this, 'down', 600);
    });
    $('.content-element').mouseleave(function() {
        $(this).removeClass('element-highlight');
        toggleElement(this, 'up', 2000);
    });

    if (isMobile) {
        $('.element-actions').each(function() {
            $(this).show();
        });
    } else {
        $('.content-element').mouseenter(function() {
            $(this).find('.element-actions').show();
        });
        $('.content-element').mouseleave(function() {
            $(this).find('.element-actions').hide();
        });
    }

};

$(function() {
    initBaseActions();
});
