from pydub import AudioSegment
from pydub.generators import Sine
from pydub.utils import make_chunks
from pyaudio import PyAudio, paInt16
from datetime import datetime, timedelta, timezone
# from requests import get
# import ntplib
from threading import Thread
from time import sleep

class WWV_gen():

    def __init__(self) -> None:
        self.sec = AudioSegment.silent(duration=1000, frame_rate=96000)
        khz_1 = Sine(1000, sample_rate=96000)
        khz_1_5 = Sine(1500, sample_rate=96000)
        self.tickSig = khz_1.to_audio_segment(duration=5, volume=-2)+self.sec[:995]
        self.tickMin = khz_1.to_audio_segment(duration=800, volume=-2)+self.sec[:200]
        self.tickHour = khz_1_5.to_audio_segment(duration=800, volume=-2)+self.sec[:200]
        self.midTickStart = AudioSegment.silent(duration=30, frame_rate=96000)
        self.midTickEnd = AudioSegment.silent(duration=10, frame_rate=96000)
        self.midTick440 = Sine(440, sample_rate=96000).to_audio_segment(duration=1960, volume=-2)
        self.midTick500 = Sine(500, sample_rate=96000).to_audio_segment(duration=1960, volume=-2)
        self.midTick600 = Sine(600, sample_rate=96000).to_audio_segment(duration=1960, volume=-2)
        bcdSig = Sine(100, sample_rate=96000)
        BCD = self.sec
        self.BCDShort = BCD.overlay(bcdSig.to_audio_segment(duration=170, volume=-9))
        self.BCDMedium = BCD.overlay(bcdSig.to_audio_segment(duration=470, volume=-9))
        self.BCDLong = BCD.overlay(bcdSig.to_audio_segment(duration=770, volume=-9))

    def genTick(self, next):
        now = datetime.utcnow()
        if next:
            now = now + timedelta(minutes=1)
            now = now.timetuple()
        else:
            now = now.timetuple()
        min = now.tm_min
        if min == 0:
            tickMin = self.tickHour
        else:
            tickMin = self.tickMin

        tickCycle = tickMin+(self.tickSig*28)+self.sec+(self.tickSig*29)+self.sec
        return tickCycle
    
    def genMidTick(self, next):
        
        now = datetime.utcnow()
        if next:
            now = now + timedelta(minutes=1)
            now = now.timetuple()
        else:
            now = now.timetuple()
        min = now.tm_min
        hour = now.tm_hour

        if min in [4, 6, 12, 14, 16, 20, 22, 24, 26, 28, 32, 34, 36, 38, 40, 42, 52, 54, 56, 58]:
            midTick = self.midTickStart+self.midTick500[:960]+self.midTickEnd
            midTickLong = self.midTickStart+self.midTick500+self.midTickEnd
            midTickCycle = self.sec+(midTick*27)+midTickLong+(midTick*15)
        elif min in [1, 3, 5, 7, 11, 13, 15, 17, 19, 21, 23, 25, 27, 31, 33, 35, 37,39, 41, 53, 55, 57]:
            midTick = self.midTickStart+self.midTick600[:960]+self.midTickEnd
            midTickLong = self.midTickStart+self.midTick600+self.midTickEnd
            midTickCycle = self.sec+(midTick*27)+midTickLong+(midTick*15)
        elif min in [2] and hour != 0:
            midTick = self.midTickStart+self.midTick440[:960]+self.midTickEnd
            midTickLong = self.midTickStart+self.midTick440+self.midTickEnd
            midTickCycle = self.sec+(midTick*27)+midTickLong+(midTick*15)
        else:
            midTickCycle = AudioSegment.empty()
        return midTickCycle
    
    def genBCDCode(self, next=False):
        now = datetime.utcnow()

        if next:
            now = now + timedelta(minutes=1)
            now = now.timetuple()
        else:
            now = now.timetuple()

        year = str(now.tm_year).rjust(4, "0")
        year_bin = format(int(year[3]), 'b').rjust(4,"0")[::-1]
        year_ten_bin = format(int(year[2]), 'b').rjust(4,"0")[::-1]

        hour = str(now.tm_hour).rjust(2, "0")
        hour_bin = format(int(hour[1]), 'b').rjust(4,"0")[::-1]
        hour_ten_bin = format(int(hour[0]), 'b').rjust(2,"0")[::-1]

        minutes = str(now.tm_min).rjust(2, "0")
        minutes_bin = format(int(minutes[1]), 'b').rjust(4,"0")[::-1]
        minutes_ten_bin = format(int(minutes[0]), 'b').rjust(3,"0")[::-1]

        days = str(now.tm_yday).rjust(3, "0")
        days_bin = format(int(days[2]), 'b').rjust(4,"0")[::-1]
        days_ten_bin = format(int(days[1]), 'b').rjust(4,"0")[::-1]
        days_hun_bin = format(int(days[0]), 'b').rjust(2,"0")[::-1]

        dst = now.tm_isdst
        # try:
        #     webLeap = get("https://hpiers.obspm.fr/eop-pc/webservice/CURL/leapSecond.php").split("|")[2]
        # except:
        #     webLeap = "Not Scheduled"
        webLeap = "Not Scheduled"
        leap = "1" if webLeap != "Not Scheduled" else "0"

        BCDCode = ["S", "0"] ## 0,1
        BCDCode.append("1") if dst > 0 else BCDCode.append("0") ## 2
        BCDCode.append(leap) ## 3
        for i in list(year_bin):
            BCDCode.append(i) ## 4, 5, 6, 7
        BCDCode.append("0") ## 8
        BCDCode.append("M") ## 9
        for i in list(minutes_bin):
            BCDCode.append(i) ## 10, 11, 12, 13
        BCDCode.append("0") ## 14
        for i in list(minutes_ten_bin):
            BCDCode.append(i) ## 15, 16, 17
        BCDCode.append("0") ## 18
        BCDCode.append("M") ## 19
        for i in list(hour_bin):
            BCDCode.append(i) ## 20, 21, 22, 23
        BCDCode.append("0") ## 24
        for i in list(hour_ten_bin):
            BCDCode.append(i) ## 25, 26
        BCDCode.append("0") ## 27
        BCDCode.append("0") ## 28
        BCDCode.append("M") ## 29
        for i in list(days_bin):
            BCDCode.append(i) ## 30, 31, 32, 33
        BCDCode.append("0") ## 34
        for i in list(days_ten_bin):
            BCDCode.append(i) ## 35, 36, 37, 38
        BCDCode.append("M") ## 39
        for i in list(days_hun_bin):
            BCDCode.append(i) ## 40, 41
        BCDCode.append("0") ## 42
        BCDCode.append("0") ## 43
        BCDCode.append("0") ## 44
        BCDCode.append("0") ## 45
        BCDCode.append("0") ## 46
        BCDCode.append("0") ## 47
        BCDCode.append("0") ## 48
        BCDCode.append("M") ## 49
        BCDCode.append("0") ## 50
        for i in list(year_ten_bin):
            BCDCode.append(i) ## 51, 52, 53, 54
        BCDCode.append("1") if dst > 0 else BCDCode.append("0") ## 55
        BCDCode.append("0") ## 56
        BCDCode.append("0") ## 57
        BCDCode.append("0") ## 58
        BCDCode.append("M") ## 59
        return BCDCode


    def genBCD(self, next=False):
        BCD = self.genBCDCode(next)
        BCDCycle = AudioSegment.silent(30)
        for i in BCD:
            if i == "S":
                BCDCycle += self.sec
            elif i == "0":
                BCDCycle += self.BCDShort
            elif i == "1":
                BCDCycle += self.BCDMedium
            elif i == "M":
                BCDCycle += self.BCDLong
        return BCDCycle[:60000]
    
    def generate(self, next=False):
        ticks = self.genTick(next)
        midTicks = self.genMidTick(next)
        BCD = self.genBCD(next)
        tickSig = ticks.overlay(midTicks)
        sig = tickSig.overlay(BCD)
        return sig
    
class WWV():
    def __init__(self, second) -> None:
        self.genClass = WWV_gen()
        stream = PyAudio()
        self.playerItems = []
        self.out = stream.open(rate=96000, channels=1, format=paInt16, output=True)
        self.genThread = Thread(target=self.generate, name="GenThread")
        self.playerThread = Thread(target=self.player, name="PlayerThread")
        if second > 45:
            print("Pre-Generating next cycle...")
            currCycle = self.genClass.generate(True) 
        elif second < 45:
            print("Pre-Generating current cycle...")
            currCycle = self.genClass.generate()
        for i in make_chunks(currCycle[44000:], 100):
            self.playerItems.append(i)

    def start(self):
        self.genThread.start()
        self.playerThread.start()

    def generate(self):
        while True:
            nextCycle = self.genClass.generate(True)
            for i in make_chunks(nextCycle, 100):
                self.playerItems.append(i)
            sleep(60)

    def player(self):
        while True:
            if len(self.playerItems) != 0:
                i = self.playerItems.pop(0)
                self.out.write(i.raw_data)


if __name__ == "__main__":
    print("Preparing, please wait...")
    now = datetime.utcnow().time()
    oof = WWV(now.second)
    print("Waiting for Sync...")
    while now.second != 45:
        print(str(now.second).rjust(2, "0")+"."+str(now.microsecond).rjust(6, "0")+"...", end="\r")
        now = datetime.utcnow().time()
    print(str(now.second).rjust(2, "0")+"."+str(now.microsecond).rjust(6, "0")+"... SYNC'D!", end="\r")
    oof.start()
    while True:
        input()


