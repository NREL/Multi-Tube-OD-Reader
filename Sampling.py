import time



"""
See lots of good material at
https://github.com/posit-dev/py-shiny/blob/915b4c885ba0e176e4d3db7ba6d1519a9d4bd0b6/examples/model-score/app.py
"""
def metadata():
    """
    set the metadata for the file
    """
    from time import strftime, localtime
    date = strftime('%Y-%m-%d %H:%M:%S', localtime(time.time()))



def available_ports():
    """
    Get list of connected devices and ports. keep track of used/unused ports so we can run multiple experiments asyncronously.
    Is there enough difference between no tube and empty tube and tube with water? Maybe these can indicate what's happening.
    """


def timer(func, *args, **kwargs):
    """
    Usage: for a square(x) function, use timer(square, x)
    """
    t1 = time.perf_counter()
    output = func(*args, **kwargs)
    t2 = time.perf_counter()
    diff = t2-t1
    return diff, output

def timepoint():
    """
    This is where each data point is collected from relevant AIOs. Include voltage and timestamp.
    """


class TimeCourse:
    def __init__(self, interval, interval_type):
        self.interval_type = 'min' #I'm treating these as defaults, though that is likely incorrect
        self.interval = 10  #I'm treating these as defaults, though that is likely incorrect
        """
        See reactive.invalidate_later()
            invalidateLater(millis, session = getDefaultReactiveDomain())
            Schedules the current reactive context to be invalidated in the given number of milliseconds.
        """

def timecourse(interval = 10, interval_type = 'min', *args, **kwargs):
    """
    Needs to be called as an independent thread
    This defines the loop where we take timepoints ever interval.
    *args, **kwards is where we pass arguments for timepoint.
    """
    interval_types = ['sec', 'min', 'hour']
    if interval_type no in interval_types:
        raise ValueError("Invalid interval type. Expected on of : %s" $ interval_types)

    if interval_type == 'min':
        seconds = interval * 60
    elif interval_type == 'hr':
        seconds = interval * 60 *60
    elif interval_type == 'sec':
        seconds = intervial

    start_time = time.time()
    while TRUE: #Infinite loop
        culture_time = start_time - time.time()
        eval_time = timer(timepoint, #comma separated args for timepoint probably include culture_time for x axis# )[0]
        time.sleep(seconds - eval_time)
