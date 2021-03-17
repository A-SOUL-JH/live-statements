import plotly
import plotly.graph_objs as go
import plotly.express as px
import plotly.io as pio
import pandas as pd
import jieba
from plotly.offline import iplot
from plotly.subplots import make_subplots
from wordcloud import WordCloud

from datetime import datetime
from jieba.analyse import extract_tags

from vdb import VDB
from settings import MEDAL_ASOUL


class ASFigure():
    def __init__(self, room):
        self.__start_time = room.start_time
        self.__end_time = room.end_time
        self.__record_time = datetime.now().strftime('%Y%m%d%H%M')
        self.rid = room.room_display_id
        self.title = room.title
        self.data = {}

        # db = VDB.get_db(self.rid)
        
        def find_args(flag):
            alpha = 1000 if flag else 1
            return [
                {'time': {'$gte': self.__start_time * alpha, '$lte': self.__end_time * alpha}},
                {'_id': False}
            ]

        for cname in VDB.get_db(self.rid).list_collection_names():
            args = find_args(cname == 'danmu')
            d = VDB.find(self.rid, cname, *args)
            if d.count():
                self.data[cname] = pd.DataFrame(d)

        if not self.data.get('superchat', pd.DataFrame()).empty:
            self.data['superchat']['price'] = self.data['superchat']['price'] * 1000
        if not self.data.get('guard', pd.DataFrame()).empty:
            self.data['guard']['coin'] = self.data['guard']['price'] * self.data['guard']['num']

        self.user_info = self.__gen_user_info()
        self.medal_info = None
    

    def word_cloud(self, topN=128):
        """直播弹幕词云图"""
        title = '直播弹幕词云'
        filename = self.__gen_filename(title)
        # 加载用户词典和停用词词典
        jieba.load_userdict('dict/user_dict.txt')

        texts = self.data.get('danmu', pd.DataFrame(columns=['uid', 'text']))['text']
        score = extract_tags('\n'.join(texts), topK=topN, withWeight=True)

        wordcloud = WordCloud(
            font_path='SourceHanSansSC-Normal.otf', 
            background_color='white',
            scale=8
        ).generate_from_frequencies(dict(score))
        wordcloud.to_file(filename)

    def popular_x_time_line(self):
        """人气值折线图"""
        title = '人气值折线图'
        filename = self.__gen_filename(title)

        df = self.data['view'].sort_values('time')
        df.loc[:,'time'] = df['time'].map(lambda x: datetime.fromtimestamp(x))

        fig = px.line(df, x='time', y='value', labels={'time': '时间', 'value': '人气值'}, title=title)
        fig.update_layout(dict(yaxis=dict(tickformat='-')))

        pio.write_image(fig, filename, scale=8)

    def medal_danmu_box(self):
        """各粉丝牌弹幕量箱型图"""
        title = '各粉丝牌弹幕量箱型图'
        filename = self.__gen_filename(title)

        data = self.user_info[['medal', 'num']]
        tmp = data.groupby('medal').count().reset_index()
        top = tmp[tmp['num']>4]['medal']
        df = data[data['medal'].isin(top)].copy()

        fig = px.box(df, x='medal', y='num', title=title, labels={'medal':'粉丝牌', 'num': '弹幕量'})

        pio.write_image(fig, filename, scale=8)

    def danmu_mean_x_time_line(self, k=(60, 300, 1200)):
        """弹幕量均线"""
        title = '弹幕量均线'
        filename = self.__gen_filename(title)
        
        data = self.data.get('danmu',pd.DataFrame(columns=['time', 'text']))[['time', 'text']].copy()
        data.loc[:, 'time'] = data['time'] // 1000

        # 统计每秒弹幕量
        tmp = data.groupby('time').count().reindex(range(self.__start_time, self.__end_time), fill_value=0).sort_index().copy()
        def kmean(interval):
            _ = tmp.rolling(interval, min_periods=1,center=False).mean().reset_index().copy()
            _['type'] = str(interval//60) + '分钟均线'
            return _
        df = pd.concat([kmean(i) for i in k])
        df.loc[:, 'time'] = df['time'].map(lambda x: datetime.fromtimestamp(x))

        fig = px.line(df, x='time', y='text', color='type', title=title, labels={'time': '时间', 'text': '弹幕量', 'type': '类型'})
        fig.update_layout(dict(xaxis=dict(tickformat='%H:%M')))

        pio.write_image(fig, filename, width=1280, height=800, scale=1.5)

    def gold_mean_x_time_line(self, k=(300, 900, 1800)):
        """金瓜子均线"""
        title = '金瓜子均线'
        filename = self.__gen_filename(title)

        gifts = self.data.get('gift', pd.DataFrame(columns=['coin', 'type', 'time']))
        superchats = self.data.get('superchat', pd.DataFrame(columns=['uid', 'price', 'time']))
        guards = self.data.get('guard', pd.DataFrame(columns=['coin', 'time']))
        data = pd.concat([
            gifts[gifts['type'] == 'gold'][['time','coin']],
            superchats[['time','price']].rename(columns=dict(price='coin')),
            guards[['time','coin']]
        ])

        # 统计每秒金瓜子
        tmp = data.groupby('time').sum().reindex(range(self.__start_time, self.__end_time), fill_value=0).sort_index()
        def kmean(interval):
            _ = tmp.rolling(interval, min_periods=1,center=False).mean().reset_index().copy()
            _['type'] = str(interval//60) + '分钟金瓜子均线'
            return _
        df = pd.concat([kmean(i) for i in k])
        df.loc[:, 'time'] = df['time'].map(lambda x: datetime.fromtimestamp(x))
    
        fig = px.line(df, x='time', y='coin', color='type', title=title, labels={'time': '时间', 'coin': '金瓜子', 'type': '类型'})
        fig.update_layout(dict(xaxis=dict(tickformat='%H:%M'), yaxis=dict(tickformat='-')))

        pio.write_image(fig, filename, width=1280, height=800, scale=1.5)

    def danmu_x_time_line(self, interval=60):
        """1分钟弹幕折线"""
        title = '{0}分钟弹幕折线'.format(interval//60)
        filename = self.__gen_filename(title)
        
        danmus = self.data.get('danmu',pd.DataFrame(columns=['time', 'text'])).copy()
        data = danmus[['time', 'text']]
        data.loc[:, 'time'] = data['time'] // 1000

        # 统计每秒弹幕量
        df = data.groupby('time').count().reindex(range(self.__start_time, self.__end_time), fill_value=0).sort_index().rolling(interval, min_periods=1,center=False).sum().reset_index()
        df.loc[:, 'time'] = df['time'].map(lambda x: datetime.fromtimestamp(x))

        fig = px.line(df, x='time', y='text', title=title, labels={'time': '时间', 'text': '弹幕量'})
        fig.update_layout(dict(xaxis=dict(tickformat='%H:%M')))

        pio.write_image(fig, filename, scale=8)

    def gold_x_time_line(self, interval=600):
        """5分钟礼物折线"""
        title = '{0}分钟礼物折线'.format(interval//60)
        filename = self.__gen_filename(title)

        gifts = self.data.get('gift', pd.DataFrame(columns=['coin', 'type', 'time']))
        superchats = self.data.get('superchat', pd.DataFrame(columns=['uid', 'price', 'time']))
        guards = self.data.get('guard', pd.DataFrame(columns=['uid', 'time']))
        data = pd.concat([
            gifts[gifts['type'] == 'gold'][['time','coin']],
            superchats[['time','price']].rename(columns=dict(price='coin')),
            guards[['time','coin']]
        ])

        # 统计每秒金瓜子
        df = data.groupby('time').sum().reindex(range(self.__start_time, self.__end_time), fill_value=0).sort_index().rolling(interval, min_periods=1,center=False).sum().reset_index()
        df.loc[:, 'time'] = df['time'].map(lambda x: datetime.fromtimestamp(x))
    
        fig = px.line(df, x='time', y='coin', title=title, labels={'time': '时间', 'coin': '金瓜子'})
        fig.update_layout(dict(xaxis=dict(tickformat='%H:%M'), yaxis=dict(tickformat='-')))

        pio.write_image(fig, filename, scale=8)

    def interact_interval_x_time_line(self, interval=600):
        """10分钟互动人数累计曲线"""
        title = '10分钟互动人数累计曲线'
        filename = self.__gen_filename(title)

        danmus = self.data.get('danmu', pd.DataFrame(columns=['uid', 'time']))
        gifts = self.data.get('gift', pd.DataFrame(columns=['uid', 'time']))
        superchats = self.data.get('superchat', pd.DataFrame(columns=['uid', 'time']))
        guards = self.data.get('guard', pd.DataFrame(columns=['uid', 'time']))

        danmus.loc[:, 'time'] = danmus['time'].map(lambda x: x//1000)
        data = pd.concat([
            danmus[['time','uid']],
            gifts[['time','uid']],
            superchats[['time','uid']],
            guards[['time','uid']]
        ])
        tmp = data.groupby('time').agg(['unique']).reindex(range(self.__start_time, self.__end_time), fill_value=[])['uid']['unique']
        d = dict(tmp)
        y = {}
        s, e = min(d), max(d)
        for i in range(s, e+1):
            res = set()
            for j in range(max(s, i-600), i+1):
                res.update(d[j])
            y[i] = len(res)
        
        df = pd.Series(y, name='uid').reset_index()
        df.loc[:, 'index'] = df['index'].map(lambda x: datetime.fromtimestamp(x))
        fig = px.line(df, x='index', y='uid', title=title, labels={'index': '时间', 'uid': '人数'})
        # fig.update_traces(line_shape='hv')
        fig.update_layout(dict(xaxis=dict(tickformat='%H:%M')))

        pio.write_image(fig, filename, scale=8)

    def interact_x_time_line(self):
        """互动人数累计曲线"""
        title = '互动人数累计曲线'
        filename = self.__gen_filename(title)

        danmus = self.data.get('danmu', pd.DataFrame(columns=['uid', 'time']))
        gifts = self.data.get('gift', pd.DataFrame(columns=['uid', 'time']))
        superchats = self.data.get('superchat', pd.DataFrame(columns=['uid', 'time']))
        guards = self.data.get('guard', pd.DataFrame(columns=['uid', 'time']))

        danmus.loc[:, 'time'] = danmus['time'].map(lambda x: x//1000)
        data = pd.concat([
            danmus[['time','uid']],
            gifts[['time','uid']],
            superchats[['time','uid']],
            guards[['time','uid']]
        ])
        df = data.drop_duplicates(subset=['uid']).sort_values('time', ascending=True).reset_index()['time']    
        df = pd.concat([df, pd.Series(range(df.shape[0]))], axis=1).rename(columns={0:'人数', 'time':'时间'})
        df.loc[:, '时间'] = df['时间'].map(lambda x: datetime.fromtimestamp(x))

        fig = px.line(df, x='时间', y='人数', title=title)
        fig.update_traces(line_shape='hv')
        fig.update_layout(dict(xaxis=dict(tickformat='%H:%M')))

        pio.write_image(fig, filename, scale=8)
    
    def purch_x_time_line(self):
        """付费人数累计曲线"""
        title = '付费人数累计曲线'
        filename = self.__gen_filename(title)

        gifts = self.data.get('gift', pd.DataFrame(columns=['uid', 'type', 'time']))
        superchats = self.data.get('superchat', pd.DataFrame(columns=['uid', 'price', 'time']))
        guards = self.data.get('guard', pd.DataFrame(columns=['uid', 'time']))

        data = pd.concat([
            gifts[gifts['type'] == 'gold'][['time','uid']],
            superchats[['time','uid']],
            guards[['time','uid']]
        ])
        df = data.drop_duplicates(subset=['uid']).sort_values('time', ascending=True).reset_index()['time']    
        df = pd.concat([df, pd.Series(range(df.shape[0]))], axis=1).rename(columns={0:'人数', 'time':'时间'})
        df.loc[:, '时间'] = df['时间'].map(lambda x: datetime.fromtimestamp(x))
        
        fig = px.line(df, x='时间', y='人数', title=title)
        fig.update_traces(line_shape='hv')
        fig.update_layout(dict(xaxis=dict(tickformat='%H:%M')))

        pio.write_image(fig, filename, scale=8)

    def medal_top_bar(self, topN=10):
        """互动人数排行条形图"""
        title = '互动人数前'+str(topN)+'粉丝牌(A-SOUL牌子除外)'
        filename = self.__gen_filename(title)
        LEVEL, MEDAL = 'mlevel', 'medal'

        # 统计佩戴各粉丝牌的人数
        data = self.user_info[(self.user_info[MEDAL] != '') & ~self.user_info[MEDAL].isin(MEDAL_ASOUL)][[LEVEL, MEDAL]].copy()
        top = data.groupby(MEDAL).count().sort_values(LEVEL, ascending=False).head(topN).index
        level_seg_gen = lambda x: 'Lv.'+'-'.join([str((x-1)//5*5+1), str(((x-1)//5+1)*5)]) if x else str(x)
        data['level_seg'] = data[LEVEL].map(level_seg_gen)
        df = data[data[MEDAL].isin(top)].groupby([MEDAL, 'level_seg']).count().reset_index()
        
        fig = px.bar(
            df, x=LEVEL, y=MEDAL, orientation='h',
            color='level_seg', title=title, 
            labels={LEVEL: '佩戴该粉丝牌人数', MEDAL:'粉丝牌', 'level_seg':'粉丝牌等级区间'},
            category_orders={MEDAL: top, 'level_seg': list(map(level_seg_gen, range(1,60,5)))}
        )
        fig.update_layout({
            'xaxis': dict(side='top'),
            'margin': dict(t=150)
        })
        pio.write_image(fig, filename, scale=8)

    def medal_top_sunburst(self, topN=10):
        """互动人数排行旭日图"""
        title = '互动人数前'+str(topN)+'粉丝牌(A-SOUL牌子除外)'
        filename = self.__gen_filename(title)
        LEVEL, MEDAL = 'mlevel', 'medal'

        # 统计佩戴各粉丝牌的人数
        df = self.user_info[[LEVEL, MEDAL]].copy()
        top = df[(df[MEDAL] != '') & ~df[MEDAL].isin(MEDAL_ASOUL)].groupby(MEDAL).count().sort_values(LEVEL, ascending=False).head(topN).index
        df['level_seg'] = df[LEVEL].map(lambda x: 'Lv.'+'-'.join([str((x-1)//5*5+1), str(((x-1)//5+1)*5)]) if x else str(x))

        fig = px.sunburst(df[df[MEDAL].isin(top)], path=[MEDAL, 'level_seg', LEVEL], title=title, maxdepth=2)
        fig.update_traces(hovertemplate='<b>%{label} </b><br>人数：%{value}')

        pio.write_image(fig, filename, scale=8)

    def medal_guard_sunburst(self):
        """大航海D情态势"""
        title = '大航海D情态势'
        filename = self.__gen_filename(title)
        LEVEL, MEDAL = 'mlevel', 'medal'

        # 提取弹幕发送者粉丝牌信息，根据uid去重，新建DataFrame
        df = self.user_info[[LEVEL, MEDAL]].copy()

        fig = px.sunburst(df[(df[LEVEL] > 22) & ~df[MEDAL].isin(MEDAL_ASOUL)], path=[LEVEL, MEDAL], title=title, maxdepth=2)
        fig.update_traces(hovertemplate='<b>%{label} </b> <br>人数：%{value}')

        pio.write_image(fig, filename, scale=8)

    def medal_all_sunburst(self):
        """直播观众粉丝牌构成"""
        title = '直播观众粉丝牌构成'
        filename = self.__gen_filename(title)
        LEVEL, MEDAL = 'mlevel', 'medal'

        df = self.user_info[[LEVEL, MEDAL]].copy()
        df.loc[df[MEDAL]=='', MEDAL] = '未戴牌子'
        df.loc[df[MEDAL].isin(MEDAL_ASOUL), 'group'] = 'A-SOUL'
        df.loc[~df[MEDAL].isin(MEDAL_ASOUL), 'group'] = '其他'

        fig = px.sunburst(df, path=['group', MEDAL], title=title, maxdepth=2)
        fig.update_traces(hovertemplate='<b>%{label} </b> <br>人数：%{value}')

        pio.write_image(fig, filename, scale=8)

    def gift_composition_bar(self):
        """礼物构成"""
        title = '直播金瓜子收益结构'
        filename = self.__gen_filename(title)

        gifts = self.data.get('gift', pd.DataFrame(columns=['uid', 'type', 'coin', 'num']))
        gifts['price'] = gifts['coin'] / gifts['num']
        superchats = self.data.get('superchat', pd.DataFrame(columns=['uid', 'price']))
        superchats['num'] = 1
        guards = self.data.get('guard', pd.DataFrame(columns=['uid', 'price', 'num']))
        gifts['src'] = '礼物'
        superchats['src'] = '醒目留言'
        guards['src'] = '大航海'
        gold = pd.concat([
            gifts[gifts['type']=='gold'][['price', 'num', 'src']],
            superchats[['price', 'num', 'src']],
            guards[['price', 'num', 'src']]
        ])
        c = [gold['price'] <= 0] + [gold['price'] < (10**i * 10000) for i in range(4)]
        for i in range(len(c) - 1):
            gold.loc[~c[i] & c[i+1], '价位'] = '{0}-{1}'.format(10**i if i else 0, 10**(i+1))
        else:
            gold.loc[~c[i+1], '价位'] = '{0}以上'.format(10**(i+1))
        gold['coin'] = gold['price'] * gold['num']
        total = gold[['价位', 'src', 'coin']].groupby(['价位', 'src']).sum().reset_index().rename(columns=dict(src='金瓜子来源', coin='金瓜子'))

        fig = px.bar(total, x='价位', y='金瓜子', color='金瓜子来源', title=title)

        pio.write_image(fig, filename, scale=8)

    def describe(self):
        """生成描述文件"""
        fn = self.__gen_filename('', ext='')
        desc = '\n'.join([str(self.__start_time), str(self.__end_time), self.title, str(self.rid), self.statistic()])
        print(desc)
        with open(fn, 'w') as f:
            f.write(desc)

    def statistic(self):
        ui = self.user_info
        desc = """直播数据统计：
        开始时间：{stime} 结束时间：{etime}
        直播时长：{duration}
        互动人数：{pnum} / {dpnum} / {gpnum}
        弹幕总量：{dnum}
        人均弹幕：{dmean} / {dmean_all}
        金瓜子总量：{gnum}
        人均金瓜子：{gmean} / {gmean_all}"""
        dur = self.__end_time - self.__start_time
        data = dict(
            stime=datetime.fromtimestamp(self.__start_time).strftime('%Y-%m-%d %H:%M:%S'),
            etime=datetime.fromtimestamp(self.__end_time).strftime('%Y-%m-%d %H:%M:%S'),
            dnum=ui['num'].sum(),
            dpnum= ui[ui['num'] != 0]['num'].count(),
            dmean= ui[ui['num'] != 0]['num'].mean(),
            gnum = ui['gold'].sum(),
            gpnum = ui[ui['gold'] != 0]['gold'].count(),
            gmean = ui[ui['gold'] != 0]['gold'].mean(),
            pnum = ui['num'].count(),
            dmean_all=ui['num'].mean(),
            gmean_all=ui['gold'].mean(),
            duration="{:02}:{:02}:{:02}".format(*[dur//3600, dur%3600//60, dur%3600%60])
        )
        return desc.format(**data)
    
    def paint(self):
        """绘制一场直播的所有统计图表"""
        self.describe()
        self.word_cloud()
        self.popular_x_time_line()
        self.danmu_mean_x_time_line()
        self.gold_mean_x_time_line()
        self.interact_interval_x_time_line()
        self.purch_x_time_line()
        self.medal_top_bar()
        self.medal_guard_sunburst()
        self.medal_all_sunburst()
        self.gift_composition_bar()

    def __gen_filename(self, gtitle, base='figure', ext='.png'):
        """生成图表文件名"""
        return base + '/{0}#{1}#{2}#{3}{4}'.format(self.__record_time, self.rid, self.title, gtitle, ext)

    def __gen_medal_info(self):
        df = self.data['danmu']

    def __gen_user_info(self):
        """生成如下格式用户数据
            用户 粉丝牌 粉丝牌等级 弹幕量 付费量
        """
        danmus = self.data.get('danmu', pd.DataFrame(columns=['uid', 'text', 'medal']))
        gifts = self.data.get('gift', pd.DataFrame(columns=['uid', 'type', 'coin', 'medal']))
        superchats = self.data.get('superchat', pd.DataFrame(columns=['uid', 'price', 'medal']))
        guards = self.data.get('guard', pd.DataFrame(columns=['uid', 'coin']))

        dm = danmus[['uid', 'text']].groupby('uid').count().rename(columns=dict(text='num'))
        silver = gifts[gifts['type'] == 'silver'][['uid','coin']].copy()
        silver['coin'] = 0
        gold = pd.concat([
            gifts[gifts['type'] == 'gold'][['uid','coin']],
            superchats[['uid','price']].rename(columns=dict(price='coin')),
            guards[['uid','coin']],
            silver
        ]).groupby('uid').sum().rename(columns=dict(coin='gold'))
        medal = pd.concat([danmus[['uid','medal']], superchats[['uid','medal']], gifts[['uid','medal']]]).drop_duplicates(subset=['uid'])
        medal[['mlevel', 'medal']] = medal['medal'].apply(pd.Series)
        temp = pd.concat([dm, gold, medal.set_index('uid')['mlevel']], axis=1).fillna(0).astype(int)

        return pd.concat([temp, medal.set_index('uid')['medal']], axis=1).fillna('未知牌子')


# 直播关注人数和粉丝团人数折线图
def follow_line():
    data = fans.rename(columns={'fans':'关注人数', 'fans_club': '粉丝团人数'})
    fig = px.scatter(data, x='time', y=['关注人数', '粉丝团人数'], labels=dict(value='关注人数', variable='关注和粉丝团', time='时间'))
    fig.data[1].yaxis = 'y2'
    fig.update_layout(dict(yaxis2=dict(anchor='x', overlaying='y', side='right', title={'text': '粉丝团人数'}),legend=dict(x=1.05)))
    iplot(fig)


# 直播关注人数和粉丝团人数散点图
def follow_scatter():
    data = fans.rename(columns={'fans':'关注人数', 'fans_club': '粉丝团人数'})
    fig = px.scatter(data, x='关注人数', y='粉丝团人数')
    fig.update_traces(mode='lines+markers')    
    fig.update_layout(dict(yaxis2=dict(title={'text': '粉丝团人数'})))    

    iplot(fig)


# 粉丝牌、人数、人均弹幕量三元组气泡图
def medal_danmu_scatter():
    MEDAL, UID = '牌子', 'uid'
    # 提取弹幕发送者粉丝牌信息
    medal_data = pd.DataFrame(list(danmus['medal']), columns=['level', MEDAL])
    uid_medalname = pd.concat([danmus[UID], medal_data[MEDAL]], axis=1)
    # 统计各粉丝牌发送弹幕量
    dm = uid_medalname[MEDAL].value_counts().rename('弹幕量')
    # 根据uid和medal去重，统计佩戴各粉丝牌的人数
    people = uid_medalname.drop_duplicates(subset=[UID, MEDAL])[MEDAL].value_counts().rename('人数')
    tri = pd.concat([dm, people], axis=1).reset_index().rename(columns=dict(index=MEDAL)).sort_values('人数', ascending=False)
    tri['人均弹幕量'] = tri['弹幕量'] / tri['人数']

    fig = px.scatter(tri[:20], x=MEDAL, y='人数', size='人均弹幕量')
    iplot(fig)


# 用户弹幕量付费量画像
def user_danmu_gold_scatter():
    dm = danmus[['uid', 'text']].groupby('uid').count().reset_index().rename(columns=dict(text='num'))
    data = pd.concat([
        gifts[gifts['type'] == 'gold'][['uid','coin']],
        superchats[['uid','price']].rename(columns=dict(price='coin')),
        guards[['uid','coin']]
    ]).groupby('uid').sum().reset_index().rename(columns=dict(coin='gold'))
    df = pd.concat([dm, data], axis=1)

    fig = px.scatter(df, x='num', y='gold',  marginal_x='rug', marginal_y='rug')
    iplot(fig)


# 不同粉丝弹幕量排行条形图
def danmu_medal_bar(topN=15):
    MEDAL, DANMU = '牌子', '弹幕量'
    df = pd.DataFrame(list(danmus['medal']), columns=[DANMU, MEDAL]).groupby(MEDAL).count().sort_values(DANMU, ascending=False)[:topN][::-1].rename(index={'': '未带牌子'}).reset_index()
    
    fig = px.bar(df, x=DANMU, y=MEDAL, orientation='h', labels=dict(value='弹幕量'), title='各家粉丝弹幕清单前'+str(topN))
    fig.update_layout({
        'yaxis': dict(title=dict(text='牌子')),
        'xaxis': dict(side='top'),
        'legend': None,
        'paper_bgcolor':'rgb(248, 248, 255)',
        'plot_bgcolor':'rgb(248, 248, 255)'
    })
    iplot(fig)


# 不同粉丝金瓜子礼物排行条形图
def gold_medal_bar(topN=15):
    MEDAL, GOLD = '牌子', '金瓜子'
    # 礼物金瓜子
    gold_g = gifts[gifts['type']=='gold']['medal'].apply(pd.Series).join(gifts[gifts['type'] == 'gold']['coin']).rename(columns=dict(coin=GOLD))
    # 醒目留言金瓜子
    gold_s = superchats['medal'].apply(pd.Series).join(superchats['price']).rename(columns=dict(price=GOLD))
    # 金瓜子合计
    gold = pd.concat([gold_g, gold_s]).rename(columns={1:MEDAL})

    df = gold[[MEDAL,GOLD]].groupby(MEDAL).sum().sort_values(GOLD, ascending=False)[:topN][::-1].rename(index={'': '未带牌子'}).reset_index()
    fig = px.bar(df, x=GOLD, y=MEDAL, orientation='h', title='各家粉丝投喂清单前'+str(topN)+'（不含大航海）')
    fig.update_layout({
        'yaxis': dict(title=dict(text='牌子')),
        'xaxis': dict(side='top'),
        'legend': None,
        'paper_bgcolor':'rgb(248, 248, 255)',
        'plot_bgcolor':'rgb(248, 248, 255)',
    })
    iplot(fig)