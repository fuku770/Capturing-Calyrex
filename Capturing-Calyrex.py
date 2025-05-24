#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from Commands.Sender import Sender
from Commands.PythonCommandBase import PythonCommand, ImageProcPythonCommand
from Commands.Keys import KeyPress, Button, Direction, Stick, Hat
from numba import jit,njit, uint32,int32,uint64,int64,int_
from numba.experimental import jitclass

import numpy as np
import time
import datetime
import cv2
import random
from PIL import Image, ImageOps
import pyocr
import pyocr.builders
import re

class Get_Calyrex(ImageProcPythonCommand):
    NAME = 'Capturing Calyrex'

    def __init__(self, cam):
        super().__init__(cam)

        # デバック用 (黒馬厳選時のちからをすいとる後、OCRが正常に読み取れているか確認用)
        self.bugfix = True

        # 初期値 (変更なし)
        self.waza_list_0 = ["ちからをすいとる", "", "", ""]
        self.waza_list_1 = ["トリック", "まもる", "おんねん", ""]
        self.waza_list_2 = ["なげつける", "タマゴうみ", "いやしのはどう", "あまえる"]
        self.waza_list_3 = ["いやしのはどう", "アクアリング", "みずびたし", "からにこもる"]
        self.waza_pos = None
        self.waza_kirikae = True
        self.hokakuhosei = 1          
        self.tukamaetakazu = 0.5

    """
    事前準備

    共通準備
    ・バックに「ヒメリのみ」を数十個以上用意し、バックの一番上にする
      ウルボ捕獲の場合は50個以上推奨


    1. 白バドレックス
    
    手持ち1匹目 ナットレイ
    ・素早さ 76
    ・技構成 [変化技（てっぺき）、 、 、 ]

    手持ち2匹目 ミミッキュ
    ・持ち物 こだわりメガネ
    ・HS252
    ・技構成 [トリック、まもる、おんねん、 ]
      おんねんのPPを上げておく

    手持ち3匹目 ハピナス
    ・持ち物 サンのみ
    ・HB252 B↑A↓
    ・技構成 [なげつける、たまごうみ、いやしのはどう、あまえる]
      なげつける以外の技のPPを上げておく

    手持ち4匹目 カプ・レヒレ
    ・持ち物 食べ残し
    ・HB252
    ・技構成 [いやしのはどう、アクアリング、みずびたし、からにこもる]
      いやしのはどうのPPを上げておく


    2. 黒バドレックス

    手持ち1匹目 フワライド
    ・HP 504
      ひんし（だいばくはつ）後に「げんきのかけら」を使用
      HP 252に調整
    ・持ち物 こだわりスカーフ
    ・技構成 [ちからをすいとる、 、 、（だいばくはつ）]
      ちからをすいとるのPPを上げておく
    ・特性 かるわざ

    手持ち2匹目 ミミッキュ
    ・持ち物 こだわりハチマキ
    ・HS252
    ・技構成 [トリック、まもる、おんねん、 ]
      おんねんのPPを上げておく

    手持ち3匹目 ハピナス
    ・持ち物 サンのみ
    ・HB252 B↑A↓
    ・技構成 [なげつける、たまごうみ、いやしのはどう、あまえる]
      なげつける以外の技のPPを上げておく

    手持ち4匹目 カプ・レヒレ
    ・持ち物 食べ残し
    ・HB252
    ・技構成 [いやしのはどう、アクアリング、みずびたし、からにこもる]
      いやしのはどうのPPを上げておく


    準備用TIPS
    ・こだわりハチマキ  2番道路(水上を右に進む)
    ・こだわりメガネ    スパイクタウン
    ・こだわりスカーフ  ナックルシティの駅の左から上がれる高台の家の前で「ふるびたてがみ」を預かり、
                       アラベスクタウンの左手前の家の中にいるフランク（おじさん）に渡すともらえる
    ・食べ残し         巨人のこしかけ 北東部
    ・ヒメリのみ       4・6番道路の木、見張り塔跡地など
    ・サンのみ         ダイの木

    """

    def do(self):

        # ウィジェット起動
        ret = self.dialogue6widget("設定", 
                                   [["Check", "S0 white Calyrex", False],
                                    ["Check", "A0 black Calyrex", False],
                                    ["Check", "Use ultla ball", False],
                                    ["Check", "Number of Pokemon caputured > 30", True]
                                   ])

        if ret == False:    # ウィジェットで"閉じる"または"Cancel"が選択された場合
            print("パラメータが設定されなかったためプログラムを終了します")
            self.finish()
        else:
            white_Calyrex = ret[0]
            black_Calyrex = ret[1]
            if white_Calyrex == black_Calyrex:
                print('設定に誤りがあります')
                self.finish()
            else:
                if white_Calyrex:
                    self.white_Calyrex_mode = True
                    print('白馬バドレックス S0厳選を開始します')
                else:
                    self.white_Calyrex_mode = False
                    print('黒馬バドレックス A0厳選を開始します')
            if ret[2]:
                self.hokakuhosei = 0.1
            if not ret[3]:
                self.tukamaetakazu = 0

        self.gensen_Calyrex()

        self.zyunbi()

        henka_list = self.collect_rand()

        result, seed_0, seed_1 = Calc.calc_seed(henka_list)

        rng = Xoroshiro(seed_0, seed_1)
        n = len(henka_list)*2
        f_check = self.check_advance_critical
        f_battle = self.battle_critical

        rng.get_next_rand_sequence(n)
        state = rng.get_state()
        print("現在state")
        print(hex(state[0]),hex(state[1]))
        self.export_seed(state[0], state[1])

        E, G = self.calc_hokakuritu(hp_max = 100,
                                    hp = 100,
                                    hosokuritu = 3,
                                    hokakuhosei = self.hokakuhosei,
                                    tukamaetakazu = self.tukamaetakazu)
        
        num = 0
        while True:
            advance = self.find_catch_advance(rng, num, g=int(G), e=E)
            print(f"目標消費：{advance} {n+advance}")

            copy = rng.deepcopy()
            copy.get_next_rand_sequence(advance)
            print(f"狙う乱数値：{copy.nextInt(65536)[0]}, {copy.nextInt(65536)[0]}, {copy.nextInt(65536)[0]}, {copy.nextInt(65536)[0]}, {copy.nextInt(65536)[0]}")
   
            result, count = f_check(rng, advance)
            if result:
                break
            else:
                num += advance+1
            
        f_battle(rng, advance, False, count)

        self.discord_image('捕獲可能です')
        self.finish()

    def ocr_hp(self):
        tools = pyocr.get_available_tools()
        if len(tools) == 0:
            print("OCRツールが見つかりませんでした")
            self.finish()		
        tool = tools[0]

        img = self.camera.readFrame()	
        img = Image.fromarray(img)

        #座標を指定,左,上,右,下の順
        cropimg = img.crop((15, 664, 65, 695))

        gray = ImageOps.grayscale(cropimg)
        binary = gray.point(lambda x: 0 if x < 128 else 255, '1')  # 二値化

        txt = tool.image_to_string(binary, lang="eng", builder=pyocr.builders.TextBuilder())
        txt = re.sub(r'\D', '', txt)

        try:
            return int(txt)
        except ValueError:
            return None

    def gensen_Calyrex(self):
        i = 0
        while True:
            i += 1
            print('',str(i) + "回目 実行日時：",datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S'))
            while not self.isContainTemplate('Calyrex/encount_Calyrex.png', threshold=0.7, show_value=False):
                self.press(Button.A, 0.1, 0.1)
            while not self.isContainTemplate('Calyrex/battle.png', threshold=0.7, show_value=False):
                self.press(Button.B, 0.1, 0.1)
            self.press(Button.A, wait=0.5)
            self.press(Button.A, wait=0.1)
            if self.white_Calyrex_mode:
                while not self.isContainTemplate('Calyrex/Calyrex.png', threshold=0.7, show_value=False):
                    if self.isContainTemplate('Calyrex/Ferrothorn.png', threshold=0.7, show_value=False):
                        self.wait(1.5)
                        self.discord_image('S0 or S1個体が出現しました')
                        return
                    else:
                        pass
            else:
                while not self.isContainTemplate('Calyrex/Calyrex.png', threshold=0.7, show_value=False):
                    self.wait(0.05)
                while not self.isContainTemplate('Calyrex/Drifblim.png', threshold=0.7, show_value=False):
                    self.wait(0.05)
                self.wait(0.5)
                while not self.isContainTemplate('Calyrex/Drifblim.png', threshold=0.7, show_value=False):
                    self.wait(0.01)
                while True:
                    Drifblim_hp = self.ocr_hp()
                    if Drifblim_hp:
                        if self.bugfix:
                            print(str(Drifblim_hp))
                        break
                if Drifblim_hp == 252 + 126:
                    self.discord_image('A0 or A1個体が出現しました')
                    return
            print('-> リセットします')
            self.reset()

    def zyunbi(self):
        # ナットレイ
        if self.white_Calyrex_mode:
            if not self.check_down(1):
                self.irekae(1)
        # フワライド
        else:
            self.waza_list = self.waza_list_0
            self.waza_pos = 0
            while True:
                if self.check_down(1):
                    break
                else:
                    self.use_waza(0)

        # ミミッキュ
        if self.check_down(2):
            print('準備失敗（ミミッキュ）')
            self.finish()
        self.waza_list = self.waza_list_1
        self.waza_pos = 0
        self.use_waza(0)
        if self.check_down(2):
            pass
        else:
            for _ in range(8):
                self.use_waza(2)
                if self.check_down(2):
                    break
                else:
                    if _ == 7:
                        self.irekae(2)

        # ハピナス
        if self.check_down(3):
            print('準備失敗（ハピナス）')
            self.finish()
        self.waza_list = self.waza_list_2
        self.waza_pos = 0
        critical_up = False
        waruagaki = False
        if self.white_Calyrex_mode:
            self.need_heal = 70
        else:
            self.need_heal = 90
        i = 0
        while True:
            if critical_up and waruagaki:
                for _ in range(2):
                    self.use_waza(2)
                    if self.check_down(3):
                        print('準備失敗（ハピナス）')
                        self.finish()
                        return
                self.irekae(3)
                break
            self.hp_mikata, self.hp_teki = self.check_hp()
            if self.hp_teki < self.need_heal:
                self.use_waza(2)
                waruagaki = True
            elif self.hp_mikata < 70:
                self.use_waza(1)
            elif not critical_up and i > 0:
                self.use_waza(0)
                critical_up = True
            else:
                self.use_waza(3)
            i += 1
            if self.check_down(3):
                print('準備失敗（ハピナス）')
                self.finish()
                return

    def check_down(self, num):
        """手持ちのnum番目と入れ替え(0 ~ 5)"""
        while not self.isContainTemplate('Calyrex/battle.png', 0.8) and not self.isContainTemplate('Calyrex/down.png', 0.8):
            self.wait(0.2)
        if self.isContainTemplate('Calyrex/down.png', 0.8):
            self.press(Button.A, 0.1, 0.5)
            while not self.isContainTemplate('Calyrex/irekae.png', 0.8, crop=[368, 12, 524, 188], use_gray=False):
                self.wait(0.7)
            self.wait(0.5)
            self.pressRep(Hat.BTM, wait=0.5, repeat=num, duration=0.1, interval=1.0)
            self.pressRep(Button.A, wait=1.0, repeat=7, duration=0.1, interval=0.1)
            return True
        else:
            return False

    def irekae(self, num, baton=False):
        """手持ちのnum番目と入れ替え(0 ~ 5)"""
        print("ポケモン入れ替え →", num)
        while True:
            if not baton:
                self.press(Button.B,0.1,0.6)
                if self.isContainTemplate('SWSH/battlerng/battle.png', 0.8):               
                    self.press(Hat.BTM,0.1,1.0)
                    self.press(Button.A,0.1,0.5)
                    while not self.isContainTemplate('SWSH/battlerng/irekae.png', 0.8, crop=[368, 12, 524, 188], use_gray=False):
                        self.wait(0.7)
            else:
                self.wait(0.6)
            if self.isContainTemplate('SWSH/battlerng/irekae.png', 0.8, crop=[368, 12, 524, 188], use_gray=False):
                break
        self.wait(0.5)
        self.pressRep(Hat.BTM, wait=0.5, repeat=num, duration=0.1, interval=1.0)
        self.pressRep(Button.A, wait=1.0, repeat=7, duration=0.1, interval=0.1)

    def use_waza(self, x):
        while True:
            while not self.isContainTemplate('Calyrex/battle.png', 0.8):
                self.press(Button.B,0.1,0.1)           
            if x != self.waza_pos:
                self.press(Button.A,0.1,1.0)
                if self.waza_pos is None:
                    self.press(Direction.UP, 1.5, 0.5)
                    self.pressRep(Hat.BTM, wait=0.4, repeat=x-0, duration=0.1, interval=0.4)
                else:
                    n = x - self.waza_pos
                    if n % 3 ==0:
                        n //= -3
                    if n > 0:
                        self.pressRep(Hat.BTM, wait=0.4, repeat=abs(n), duration=0.1, interval=0.4)
                    else:
                        self.pressRep(Hat.TOP, wait=0.4, repeat=abs(n), duration=0.1, interval=0.4)
                self.waza_pos = x
            #連打で技使用
            self.pressRep(Button.A, wait=0.1, repeat=5, duration=0.1, interval=0.1)
            print("技を使用 :", self.waza_list[x])
            self.pressRep(Button.B, wait=0.7, repeat=6, duration=0.1, interval=0.1)
            if self.isContainTemplate('Calyrex/battle.png', 0.8):
                print("技を使用できず")
                print("PPを回復")
                self.use_item(itemran="kinomi", item_name=["himerinomi"], num=x)
                return "item"
                break
            else:
                break
        
        return None
    
    def use_item(self, itemran="kinomi", item_name=["himerinomi"], num=0):
        n = 30
        while not self.isContainTemplate('Calyrex/battle.png', 0.8):
            self.press(Button.B,0.1,0.1)
        while not self.isContainTemplate('Calyrex/bag.png', 0.8):
            self.press(Hat.BTM,0.1,0.6)
        while self.isContainTemplate('Calyrex/bag.png', 0.8):
            self.press(Button.A,0.1,1.0)
        while not self.isContainTemplate('Calyrex/'+itemran+'.png', 0.88):
            self.press(Hat.RIGHT,0.1,0.7)
        for _ in range(n):
            for item in item_name:
                flag = False
                start = time.time()
                while time.time()-start<1:
                    if self.isContainTemplate('Calyrex/'+item+'.png', 0.8, use_gray=False):
                        flag = True
                if flag:
                    print("アイテムを使用")
                    if item == "himerinomi":
                        self.pressRep(Button.A, wait=1.0, repeat=3, duration=0.1, interval=1.0)
                        self.pressRep(Hat.BTM, wait=1.0, repeat=num, duration=0.1, interval=1.0)
                    self.pressRep(Button.A, wait=0.1, repeat=10, duration=0.1, interval=0.1)
                    return True
            else:
                self.press(Hat.BTM,0.1,0.7)
        else:
            while not self.isContainTemplate('Calyrex/bag.png', 0.8):
                self.press(Button.B,0.1,0.1)
            self.press(Hat.TOP,1.0,0.5)
            print("アイテムを使えませんでした")
            self.finish()
            return False
    
    def collect_rand(self, num=128):
        self.waza_list = self.waza_list_3
        self.waza_pos = 0
        rand_list = []
        
        while True:
            while not self.isContainTemplate('Calyrex/battle.png', 0.8):
                self.press(Button.B,0.1,0.1)
            print(f"\n残り{num-len(rand_list)}回計測")
            self.hp_mikata, self.hp_teki = self.check_hp()
            if self.hp_teki < self.need_heal:
                move = self.use_waza(0)
            else:
                if self.waza_kirikae:
                    move = self.use_waza(1)
                    self.waza_kirikae = False
                else:
                    move = self.use_waza(3)
                    self.waza_kirikae = True
            #急所を観測
            rand_list.append(self.check_critical())
            if move == "item":
                while not (self.isContainTemplate('Calyrex/battle.png', 0.8) or self.isContainTemplate('Calyrex/bag.png', 0.8)):
                    self.press(Button.B,0.1,0.1)
                self.press(Hat.TOP,1.0,0.5)
            if len(rand_list) >= num:
                break
        print(rand_list)
        return rand_list

    def check_hp(self):
        img = self.camera.readFrame()
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img = img[657: 662, 16: 282]#112, 302 298, 358
        #cv2.imwrite("sample_image_mikata.png", img)
        ret, img_thresh = cv2.threshold(img, 120, 255, cv2.THRESH_BINARY)

        image_size = img_thresh.size
        white_mikata = cv2.countNonZero(img_thresh)
        #black_mikata = img_thresh.size - white_mikata 
    
        whiteAreaRatio_mikata = (white_mikata/image_size)*100
        #blackAreaRatio = (black_mikata/image_size)*100

        img = self.camera.readFrame()
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img = img[66: 71, 979: 1245]#112, 302 298, 358
        #cv2.imwrite("sample_image_teki.png", img)
        ret, img_thresh = cv2.threshold(img, 120, 255, cv2.THRESH_BINARY)

        image_size = img_thresh.size
        white_teki = cv2.countNonZero(img_thresh)
        #black_teki = img_thresh.size - white_teki
    
        whiteAreaRatio_teki = (white_teki/image_size)*100
        #blackAreaRatio = (black_teki/image_size)*100
    
        print(f"味方残りHP : {round(whiteAreaRatio_mikata, 2)} %  敵残りHP : {round(whiteAreaRatio_teki, 2)} %")

        return whiteAreaRatio_mikata, whiteAreaRatio_teki

    def check_critical(self):
        #急所を観測
        kyusyo = False
        while not (self.isContainTemplate('Calyrex/battle.png', 0.8) or self.isContainTemplate('Calyrex/bag.png', 0.8)):
            self.wait(0.2)
            if self.isContainTemplate('Calyrex/kyusyo.png', 0.8, crop=[50, 580, 1161, 685]):#175, 506, 263, 571
                print("急所被弾")
                kyusyo = True
                break
        if kyusyo:
            return 0
        else:
            print("急所被弾せず")
            return 1
    
    def calc_hokakuritu(self, 
                        hp_max = 100,
                        hp = 100,
                        hosokuritu = 3,
                        hokakuhosei = 1,
                        tukamaetakazu = 0
                        ):
        """
        hp_max：HPの最大値、
        hp：現在HP、
        hosokuritu：ポケモンごとの捕捉率、
        hokakuhosei：ボールの補正、    
        tukamaetakazu：捕まえた数倍率、
        """
        levelhosei = 1 #レベル補正
        zyoutaiizyou = 1 #状態異常補正
        hokakupower = 1 #捕獲パワー
        

        A = int(((hp_max*3 - hp*2) * 4096 * hosokuritu * hokakuhosei) + 0.5)
        B = int((A / (hp_max * 3))) * levelhosei 
        C = int((B * zyoutaiizyou) + 0.5) #状態異常
        D = int((C * hokakupower) + 0.5)
        if D > 1044480:
            D = 1044480
        E = 715827883 * tukamaetakazu * D / (4294967296 * 4096)
        G = 65536 / (1044480 / D) ** 0.1875
        #a = 
        print(f"G：{G:.2f}  E；{E:.2f}  捕獲率：{((int(G)/65536)**4)*100:.2f} %")

        return E, G

    def find_catch_advance(self,rng,num,g=23187,e=0):
        rng = rng.deepcopy()
        rng.get_next_rand_sequence(num)
        i = 0
        while True:
            copy = rng.deepcopy()
            copy.get_next_rand_sequence(i)
            if e != 0:
                critical = copy.nextInt(256)[0]
                if critical < int(e):
                    r = copy.nextInt(65536)[0]
                    if r < g:
                        print("クリティカル")
                        return i+num                 
            for _ in range(0, 4):
                r = copy.nextInt(65536)[0]
                if r >= g:
                    break
            else:
                return i+num
            i += 1

    def check_advance_critical(self, rng_, remains_):

        count = 0
        while True:
            rng = rng_.deepcopy()
            mahi = False
            count_ = count
            remains = remains_
    
            while True:
                #self.wait(0.00001)  
                if remains <= 0:
                    break                             
                if remains == count_:
                    r, n = rng.nextInt(100)
                    remains -= n
                #痺れない場合は相手が動く
                #print(f"{remains} {remains_} {count_}")
                rng.next()  
                rng.next()               
                remains -= 2
            
            if remains == 0:
                print("ok")
                # print(lst, count)
                # print(remains)
                return True, count
            
            if remains_ < count:
                print("調節できない")
                return False, 0
                self.finish()

            if remains < 0:
                count += 1
                continue
    
    def battle_critical(self, rng, remains, check_rank=True, count=0):
  
        self.waza_list = self.waza_list_3
        self.waza_pos = None
        turn = 0
        while True:
            while not self.isContainTemplate('Calyrex/battle.png', 0.8):
                self.wait(0.2)
            print(f"\n{turn+1} ターン目\n残り消費：{remains}")
            if remains <= 0:
                break            
            if remains == count:
                move = self.use_waza(2)
                r, n = rng.nextInt(100)
                remains -= n
            else:
                move = self.use_waza(0)
            r, n = rng.nextInt(2)  
            rng.next()
            if r == 0:
                print("急所に被弾")
            else:
                print("急所に被弾せず")               
            remains -= 2
            if move == "item":
                while not (self.isContainTemplate('Calyrex/battle.png', 0.8) or self.isContainTemplate('Calyrex/bag.png', 0.8)):
                    self.press(Button.B,0.1,0.1)
                self.press(Hat.TOP,1.0,0.5)

            turn += 1
                   
        if remains < 0:
            print("消費オーバー")
            return False
        else:
            print("消費成功")
            print(f"使用する乱数値：{rng.nextInt(65536)[0]}, {rng.nextInt(65536)[0]}, {rng.nextInt(65536)[0]}, {rng.nextInt(65536)[0]}, {rng.nextInt(65536)[0]}")
            return True
        
    def export_seed(self,seed_0,seed_1):
        # ファイルに書き込む
        path = './Commands/PythonCommands/seed_swsh.txt'
        with open(path, 'w') as file:
            file.write(f"{hex(seed_0)},{hex(seed_1)}")
        print(f"seedをtxtファイルに出力しました\n{path}")
    
    def reset(self):
        self.press(Button.HOME, wait=1.0)
        self.press(Button.X, wait=0.5)
        self.press(Button.A, wait=2.0)
        while self.isContainTemplate('Calyrex/game_end.png', threshold=0.85, show_value=False):
            self.wait(0.1)
        self.wait(0.5)
            
        #いつも遊ぶ本体ではない
        self.press(Button.A, wait=0.5)
        while not self.isContainTemplate('Calyrex/user_select.png', threshold=0.85, show_value=False):
            self.wait(0.1)  
        self.press(Button.A, wait=2.0)

        while not (self.isContainTemplate('Calyrex/OP2.png', threshold=0.7, show_value=False) or self.isContainTemplate('Calyrex/OP0.png', threshold=0.7, show_value=False)):
            self.wait(0.1)
        self.press(Button.A)
        self.press(Button.A)
        
@njit
def to_binary_list(num, length):
    result = []
    while num > 0:
        result.append(num % 2)
        num //= 2
    result.reverse()
    result = [0] * (length - len(result)) + result
    return result

@njit
def binary_list_to_decimal(binary_list):
    decimal = np.uint64(0)
    for bit in binary_list:
        decimal = (decimal << 1) | np.uint64(bit)
    return decimal
    
class Calc():  
    def calc_seed(rand_list):
        N = len(rand_list)
        B = np.array([rand_list])
        inverse_matrix = InverseMatix.inverse_matrix
        inverse_matrix = [format(x, '064b') for x in inverse_matrix]
        inverse_matrix = np.array([[int(bit) for bit in binary] for binary in inverse_matrix], dtype=object)
        for i in range(len(inverse_matrix)):
            while len(inverse_matrix[i]) < 128:
                inverse_matrix[i].insert(0, 0)

        lst = []
        for j in range(N):
            a = 0
            for i in range(N):
                a ^= B[0][i]*inverse_matrix[j][i]
            lst.append(a)
            
        binary_string = ''.join(map(str, lst))
        binary_number = int(binary_string, 2)
        seed_0 = binary_number >> 64 & 0xFFFFFFFFFFFFFFFF
        seed_1 = binary_number & 0xFFFFFFFFFFFFFFFF

        rng = Xoroshiro(seed_0, seed_1)
        test = []
        num = 10
        count = 0
        while len(test) < num:
            test.append(rng.nextInt(2)[0])
            rng.get_next_rand_sequence(1)
            count += 1

        if test != rand_list[:len(test)]:
            print("リストが合わない")
            #print(henka_list)
            print(rand_list[:len(test)])
            print(test)
            return False, seed_0, seed_1
        else:
            # rng = Xoroshiro(seed_0, seed_1)
            # test = []
            # while len(test) < num:
            #     test.append(rng.nextInt(2))
            #     rng.get_next_rand_sequence(1)
            # print(henka_list)
            # print(test)
            return True, seed_0, seed_1 
        
    @njit
    def calc_inverse_matrix(henka_list, seed_list_test, syohi=0, c=0):
        print("検索開始", "消費:", syohi)
        N = 64 #len(henka_list)
        seed_1 = [1,0,0,0,0,0,1,0,1,0,1,0,0,0,1,0,1,0,1,1,0,0,0,1,0,1,1,1,0,1,0,1,0,0,1,0,0,0,1,0,1,0,0,1,1,1,0,1,0,1,1,0,1,0,1,0,0,1,0,1,1,0,1,1]

        lst_ = []
        for i in range(len(henka_list)):
            a = henka_list[i]
            lst_.append(a&1)

        r = Xoroshiro_matrix()
        seed_list = []
        # 計測前の消費
        for _ in range(syohi):
            r.next_()
        lst_aa = []
        while len(seed_list) < N:
            if len(seed_list) < N-c:
                tmp = r.next_()
            else:
                tmp = seed_list_test[len(seed_list)-(N-c)]
            aa = 0
            for i in range(0, 64):
                aa ^= seed_1[i]*tmp[i+64]
            lst_aa.append(aa)
            lst = []
            for a in range(64):
                lst.append(tmp[a])
            seed_list.append(lst)
            
        seed_list = np.array(seed_list,dtype=np.int64)

        # 単位行列を作成
        I = np.eye(N, dtype=np.int64)
        # 拡張行列を作成
        extended_matrix = np.concatenate((seed_list, I), axis=1)

        n = 1
        max = 2**(N-len(henka_list))
        #max = 0xFFFF
        for number in range(max):
            # if (number/max) >= n*0.1:
            #     print(n)
            #     n += 1
            lst = lst_
            binary_lst = to_binary_list(number, N-len(henka_list))        
            binary_lst = lst + binary_lst   
            binary_array = np.array(binary_lst,dtype=np.int64)

            for i in range(N):
                binary_array[i] ^= lst_aa[i]

            # 逆行列を求める
            for i in range(N):
                for j in range(N):
                    if i == j:
                        x = 1
                    else:
                        x = 0
                    if extended_matrix[j][i] != x:
                        for k in range(i, N):
                            if not j == k:
                                if extended_matrix[k][i] == 1:
                                    extended_matrix[j] ^= extended_matrix[k]
                                    break
                        if extended_matrix[j][i] != x:
                            print("計算失敗", "\n", j,i)
                            return -1, np.uint64(0), np.uint64(0)   

            inverse_matrix = extended_matrix[:, N:]
        #np.savetxt('matrix.txt', inverse_matrix, fmt='%d')
        #inverse_matrix = np.loadtxt('matrix.txt', dtype=int)
            
            lst_1 = []
            for j in range(N):
                a = 0
                for i in range(N):
                    a ^= binary_array[i]*inverse_matrix[j][i]
                lst_1.append(a)
            
            seed_0 = binary_list_to_decimal(lst_1)
                
            rng = Xoroshiro(seed_0, 0x82A2B175229D6A5B)
            rng.get_next_rand_sequence(syohi)
                        
            num = 32      
            test_ = []
            for i in range(num):
                test_.append(rng.nextInt(4)[0])

            if test_ != henka_list[:len(test_)]:
                # print("リストが合わない")
                # #print(henka_list)
                # print(henka_list[:len(test_)])
                # print(test_)
                continue
                
            else:
                rng = Xoroshiro(seed_0, 0x82A2B175229D6A5B)
                seed_0, seed_1 = np.uint64(seed_0), np.uint64(0x82A2B175229D6A5B)
                #print(seed_0, seed_1)
                return 1, seed_0, seed_1

            
        return 0, np.uint64(0), np.uint64(0)   

spec_0 = [
    ('seed_0',int64[:,:]),
    ('seed_1',int64[:,:]),
]

@jitclass(spec_0)
class Xoroshiro_matrix():
    
    def __init__(self):
        self.seed_0 = self.generate_unit_matrix(128)[:64]
        self.seed_1 = self.generate_unit_matrix(128)[64:]

    def generate_unit_matrix(self, n):
        unit_matrix = np.eye(n, dtype=np.int64)
        return unit_matrix

    def rotl(self, x, k):
        first_rows = x[:k]
        x = x[k:]
        x = np.vstack((x, first_rows))
        return x
    
    def shift(self, x, k):
        zeros = np.zeros((k, 128), dtype=np.int64)
        result = np.concatenate((x[k:], zeros), axis=0)
        return result

    def next_(self):       
        result = self.seed_0[-1]^self.seed_1[-1]
        self.seed_1 ^= self.seed_0
        self.seed_0 = self.rotl(self.seed_0, 24) ^ self.seed_1^self.shift(self.seed_1, 16)
        self.seed_1 = self.rotl(self.seed_1, 37)
        return result

spec = [
    ('seed_0',uint64),
    ('seed_1',uint64),
]

@jitclass(spec)
class Xoroshiro():
    def __init__(self, s0, s1):
        #self.seed = [seed, 0x82A2B175229D6A5B]
        self.seed_0 = s0 & 0xFFFFFFFFFFFFFFFF
        self.seed_1 = s1 & 0xFFFFFFFFFFFFFFFF
        #print(self.seed_0, self.seed_1)

    def rotl(self, x, k):
        return ((x << k) | (x >> (64 - k))) & 0xFFFFFFFFFFFFFFFF

    def nextP2(self, x):
        x -= 1
        for i in range(6):
            x |= x >> (1<<i)
        return x

    def next(self):
        result = (self.seed_0 + self.seed_1) & 0xFFFFFFFFFFFFFFFF

        self.seed_1 ^= self.seed_0
        self.seed_0 = self.rotl(self.seed_0, 24) ^ self.seed_1 ^ ((self.seed_1 << 16) & 0xFFFFFFFFFFFFFFFF)
        self.seed_1 = self.rotl(self.seed_1, 37)

        return result & 0xFFFFFFFF
    
    def prev(self):
        s = (self.seed_1 << 27) | (self.seed_1 >> 37)
        t = self.seed_0 ^ (s << 16)
        t = ((t << 40) | (t >> 24)) ^ ((self.seed_1 << 3) | (self.seed_1 >> 61))
        self.seed_0 = t
        self.seed_1 = t ^ s
    
    def get_next_rand_sequence(self,length):
        """Generate a the next random sequence of length"""
        return [self.next() for _ in range(length)]

    def get_state(self):
        return [self.seed_0,self.seed_1]

    def set_state(self,seed_0,seed_1):
        """Set state of the RNG"""
        self.seed_0 = np.uint64(seed_0)
        self.seed_1 = np.uint64(seed_1) 
        
    def nextInt(self, num = 0xFFFFFFFF):
        count = 0
        num2 = self.nextP2(num)
        s = self.next() & num2
        count += 1
        while s >= num:
            s = self.next() & num2
            count += 1
        return s, count
       
    def deepcopy(self) -> 'Xoroshiro':
        return Xoroshiro(self.seed_0, self.seed_1)

class InverseMatix():

    inverse_matrix = \
    [0x3c2c3861245b20c33942a26c904a523c, 0xbd3267cfcb92048b4eca1e7abece1849,
    0xe7be8f465803528a0bc6f73de4471efd, 0xd95e9f37792f076ed7bd5564a1052d78,
    0x5b72925867de5a91e3c71771dec08fbc, 0x866cef0113d5d35feaf6c355409804e4,
    0x3f001b7f6ac6cd3d11f7aebd25b7b08c, 0xd86b77d2f4491aa6fe3a194711752dc3,
    0x17bb2419d81eb086d9f9864cbe7a71c8, 0x37ef4d3262317aa2355a4870151e78c5,
    0xaff86bce247d1207ed212be6cd61063, 0xee4d5924eadbe2eba20cdeb53516ca3,
    0x6f6dfa1eac6e5eb2c7b739e9f7923457, 0xfcaac731fff2eb267c48f8dd8a0b5183,
    0xfc259e5daaacb27371535d5a38b15862, 0xf74637d35d8690c97cbe001c320915df,
    0x67ca63f21cafecc473072cd07785d190, 0x311066ff0fe3c9bd6d861e99385da41c,
    0x8424520da26cfec9a2f88cd56bdf4ce8, 0x8a6cf438330000b5297d740a106840d7,
    0x84f6fa54854173fb7cc8d06977a224c9, 0x967ae05950cb374a2edbe957bf2b618b,
    0x6195bc3c7f19e3eba1de06b5079da61d, 0xd4c594d0c8eff166589428ceebe39332,
    0x1f0c3145885503dd97ff4cd212cc4c1a, 0x82ab1b1ac578e8aff717948be16b339e,
    0xb00b07137dd538b7a803fffa04da4b13, 0xaaa6803f01464edfaa690f8733141936,
    0xb3ab54988ee07bb05cf6b5b87e60175f, 0xd85cbe35b5d886c748049b3d1db42999,
    0x90f27a3a7729e888ed62f9acd8209e2f, 0x1cd527ce92370f37f508961d671a3e7,
    0x2865472e5e4515e98638a04a97f3fec8, 0x7f63a0e3cfc0ab61b8295a45399380e7,
    0xf5d77e82781d0d941e32312081c60789, 0xa053862a4c683ce2afb0736f7a05d2ad,
    0xdb5cdd512df0aedc705366c777b6d761, 0x2a1e79785a89f36bd1649f41a91b01e,
    0x8ae5c9484ea0d82bb6477104ee6f454a, 0xfb64d89faafdfedc7b0dff080e8a70de,
    0x88ce72eb69527f8b0e5a8a71f312f123, 0xf15d395a330d060abe6b3172cbf147a4,
    0xcdfc3eabda98c8103ef935dde9851fb8, 0xd19091b6ca406cc54c0621638c733cc1,
    0xefd97546b19b8dc66f897f01141bf131, 0xb715ca1e9f8a51426a002e5f3994f09a,
    0x9c8c4a2ac373affb74a74c050ffc5ff2, 0x81f02d4158edefb82f14dabcd1e47293,
    0x75070671a85f96ee4e385a89984b0a20, 0x98b276b091ab1f435b530de252eeb86c,
    0x7d36be8ee39140d837e4c0315eec1969, 0xc24842eb3ad0faa901a8d11cf125d0d7,
    0xc712e939ede50e2cd659799052fad236, 0x90a86d50c84163331553113e3f69f061,
    0x6f16586b87e59d4c6ea976210aed3234, 0x780fb1962f8461bf816c50f5c9f7751b,
    0xe88b609e512f90f50c8ba78d07710455, 0x960650d0ea6aff0cc6b477119d3872b7,
    0x1a1a37bbeab4c2da03da592279222ccf, 0x757ab918d25f35a1af73f2424584f7a2,
    0x6b48cb56a61a394abdf24b1394c855ee, 0xdd546702bc447225a9423cef66b89b78,
    0xc780c2abe4caed32829a3f880d5831c8, 0xf725f29afbca4bdb6e1c7824e61783cc,
    0x28566b9a0cbaae9be66784668b5a81ac, 0xaf7645d9fd45f0a62f7c5ce271bb246,
    0x9b0f7a1c70717a2cb5a8efe18c7df8ae, 0xb4d216dc245d5bf2fd2f47e85e1179db,
    0xd12c205936c70a8e1e2bd16ce668d6b4, 0x743da565c1c094a9672f0fb1b7787844,
    0xeafd49247f142c10f38b864a03a57109, 0xad27ac88c559b1da8063d15562c6d95d,
    0xc9904b9145bd619a30c6ada89c1c89c7, 0x480844f4a1f88c0fba853fb3d69a10a7,
    0x926859276b00cb8c528a29d531494fe6, 0x47832e027485f4879054c96a4b10fdfd,
    0xb122c78a3ad2cf2ebf0b378a864b2956, 0x9f761fe9a32e96360794bb4ae8861500,
    0x2ac78d146212b2920f1f7c638cabd6fa, 0x2ddde6050824fe21962756292211f305,
    0xfba4ed8dadae3340ec58592c836abe42, 0x759716f8065a520d6f793d48f2eebc48,
    0xc9e08b224b53663c7f8d41745530ae14, 0x12270e61b386355b0bfa4ac4b5e64849,
    0xc3a3c81c34c45db913ea39c34982929a, 0xbb377ed7bf8af8519863d6761861d885,
    0x85ae3f890c300f8efb75e0a35ccac7de, 0xbfbf706ca83a37c7739b9a4a870cd864,
    0x70055430cb2f2c8cbc0c52073fb5a133, 0x96e7eaa29ccd5d5532cda439712e1386,
    0x2c6eaf5342211e682993148672f7052b, 0xb7d04390b596c6190334725c9ed649d3,
    0x43da6a2929bd66665fe4164ab13b5da6, 0xca298feb0aa1648d989e9dd4ae86a15,
    0xc1b5077231e8d7e2a5818c257e5492c3, 0xf8c09f854ae6b996ba76741677c1c864,
    0x41938cc5774267311485a9634945c637, 0x606e7c32f4d2bd1145d0b30523cdbf01,
    0x25793db06125403430620ef6660d00e8, 0x91e2ae8de999f8de6b3265b2df5ffecc,
    0x19ab47c22afe0a1e97cc18c0d46fd6c6, 0x4e547374a02774ab40cbb374d98874af,
    0xdae194d342f94386406016cf04ff6a5c, 0xfc4ee66c20c1a78c7713fdeb88b01a68,
    0x37705b35c3e5e9475524b32c54f7ed49, 0xf39da249f8025f2c2d68917688f95b92,
    0x6a70cbfc87442f326c1c551e71780094, 0xc0965d91cf0a0d1d10999326c9b1cd28,
    0xe29e860439ef30f25dbe8b8dee306d6a, 0x66a3d08bebda46891b6d89fdced7e412,
    0x8491b15683b042c2cd6d5d510f997c0c, 0xd7fa4448a8a1be9a97493ebb66154ef0,
    0xec35720dcbb3c9a042915bdbd5b2ac18, 0x13f7dbf29ddaee136b2738415f8235c1,
    0x5308d37ab0941c4261f33dae2a9648dc, 0xb6c63486060e329f97f4bc134958ba20,
    0x2ad84877f2dd40e4b4e50755d5642ffb, 0x8db574e7de90b76a9ea72e0982fab0fb,
    0xb48e8ee59ab48eff011bc804e6e96497, 0x1bc8fd65f0f65fbec10653a11e3d7d37,
    0xd2a9fb7dffc02c83c03e00550c1aa26d, 0x9780af69b92a27076a2400e0a7d0930a,
    0xbaad4ece5a2953ce03f71f31ce3cf7e6, 0xd437990f4e40400b69097f30253fec65,
    0xaf6c55e54c544722850ebf1fbab222f3, 0x2387379bfed144195c0d1fe7d0c33d0b,
    0xdcd7a3617044644f7ea0fdfc1708b277, 0x7725f29afbca4bdb6e1c7824e61783cc,]
    