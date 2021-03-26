from unittest.case import TestCase

from fysom import FysomGlobalMixin, FysomGlobal


def onpanic(e):
    print('onpanic! ' + e.msg)

def oncalm(e):
    print('thanks to ' + e.msg + ' done by ' + e.args[0])


def ongreen(e):
    print('green!')

def onyellow(e):
    print('yellow!')

def onred(e):
    print('red!')


class FysomModel(FysomGlobalMixin):
    def __init__(self):
        FysomGlobalMixin.GSM = FysomGlobal(
            events=[('warn', 'green', 'yellow'),
                    {
                        'name': 'panic',
                        'src': ['green', 'yellow'],
                        'dst': 'red',
                        'cond': [  # can be function object or method name
                            # 'is_angry',  # by default target is "True"
                            {True: 'is_very_angry', 'else': 'blue'},
                            {True: 'is_angry', 'else': 'turq'},
                        ]
                    },
                    ('calm', 'red', 'yellow'),
                    ('clear', 'yellow', 'green')],
            initial='green',
            final='red',
            state_field='state',
            callbacks={
                'onenter_panic_': onpanic,
                # 'on_panic': onpanic,
                'oncalm': oncalm,
                'ongreen': ongreen,
                # 'onyellow': onyellow,
                'onred': onred}
        )
        self.state = None
        super(FysomModel, self).__init__()

    def is_angry(self, event):
        return False

    def is_very_angry(self, event):
        return True

    def on_after_panic(self, e):
        print('onpanic! ' + e.msg)

    def on_leave_yellow(self, e):
        print('yellow_exit!')

    def on_yellow(self, e): #on_enter_yellow
        print('yellow_enter!')

class TestFysomModel(TestCase):

    def test_process_payouts(self):
        life_cycle = FysomModel()

        print("Current state:", life_cycle.current)

        life_cycle.warn()

        print("Current state:", life_cycle.current)

        life_cycle.panic(msg='msg_param')

        print("Current state:", life_cycle.current)

        pass
