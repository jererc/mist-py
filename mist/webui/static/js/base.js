var isMobile = isMobile();
var hasFocus = true;
var showDelays = {};


function isMobile() {
    if (navigator.userAgent.match(/iPhone|iPod|iPad|Android|WebOS|Blackberry|Symbian|Bada/i)) {
        return true;
    } else {
        return false;
    }
};

function handleFocus() {
    $(window).blur(function() {
        hasFocus = false;
    });
    $(window).focus(function() {
        hasFocus = true;
    });
};

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

function initInputFields() {
    $('.default-text').focus(function() {
        if ($(this).val() == $(this)[0].title) {
            $(this).removeClass('default-text-active');
            $(this).val("");
        }
    });
    $('.default-text').blur(function() {
        if ($(this).val() == "") {
            $(this).addClass('default-text-active');
            $(this).val($(this)[0].title);
        }
    });
    $('.default-text').blur();
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
    if (isMobile) {
        $('body').addClass('wide');
    }
    handleFocus();
    initInputFields();
    initBaseActions();
});
