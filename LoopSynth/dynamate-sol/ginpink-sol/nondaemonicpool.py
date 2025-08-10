import multiprocessing
import multiprocessing.pool

class NoDaemonProcess(multiprocessing.Process):
    """Process that is not daemon, to allow nested multiprocessing."""

    def __init__(self, *args, **kwargs):
        # Ensure no 'group' is passed to avoid Python 3.12 AssertionError
        if 'group' in kwargs:
            kwargs.pop('group')

        # Remove group if passed as first positional argument (rare but can happen)
        if len(args) > 0 and args[0] is not None:
            args = (None, *args[1:])

        super().__init__(*args, **kwargs)
        self.daemon = False

class NonDaemonicPool(multiprocessing.pool.Pool):
    """Pool with non-daemon processes to allow nested multiprocessing."""
    
    def Process(self, *args, **kwds):
        return NoDaemonProcess(*args, **kwds)

