import sys, getopt
from figure import ASFigure
from vdb import VDB


# info = [1614945600, 1614953714, "【3D】新学期晚会", 22632157]
info = [None]*4
paint_flag = True


def main(argv):
    global paint_flag, info
    try:
        opts, args = getopt.getopt(argv, "dhs:e:t:r:", ["desfile="])
    except getopt.GetoptError as e:
        print("")
        sys.exit(2)
    dicts = dict(opts)
    if '--desfile' in dicts:
        with open(dicts['--desfile']) as f:
            tmp = f.readlines()[:4]
            info[0] = int(tmp[0])
            info[1] = int(tmp[1])
            info[2] = tmp[2].strip()
            info[3] = int(tmp[3])
        del dicts['--desfile']
    for opt, arg in dicts.items():
        if opt == '-s':
            info[0] = arg
        elif opt == '-e':
            info[1] = arg
        elif opt == '-t':
            info[2] = arg
        elif opt == '-r':
            info[3] = arg
        elif opt == '-d':
            paint_flag = False
        else:
            print('python gen.py -s <starttime> -e <endtime> -t <title> -r <roomid>')


class T():
    def __init__(self, info):
        self.start_time = int(info[0])
        self.end_time = int(info[1])
        self.title = info[2]
        self.room_display_id = int(info[3])

if __name__ == '__main__':
    main(sys.argv[1:])
    VDB.set_db(int(info[3]))
    fig = ASFigure(T(info))
    if paint_flag:
        fig.paint()
    else:
        print(fig.statistic())