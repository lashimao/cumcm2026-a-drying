"""Publication figures from observed inputs and frozen numerical output."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
from drying_model import Inputs, properties
from utils.plot_style import apply_publication_style, audit_layout, audit_design, PALETTE
from utils.export_figure import export_figure


WIDTH = 16/2.54
COLORS = [PALETTE[x] for x in ['primary', 'contrast', 'positive', 'accent']]
STYLES = ['-', '--', '-.', ':']


def build_figures(input_dir, output_root):
    root = Path(output_root)
    out = root/'figures'
    out.mkdir(parents=True, exist_ok=True)
    (out/'_qa').mkdir(exist_ok=True)
    summary = json.loads((root/'results/summary.json').read_text())
    inputs = Inputs(input_dir)
    trajectories = {law: np.load(root/'results'/f'{law}_trajectory.npz')
                    for law in ['q1', 'q23', 'q4']}
    apply_publication_style(language='zh')
    plt.rcParams.update({'font.size': 9, 'axes.labelsize': 9,
                         'xtick.labelsize': 8, 'ytick.labelsize': 8,
                         'legend.fontsize': 8, 'axes.titlesize': 9,
                         'font.sans-serif': ['PingFang SC', 'DejaVu Sans']})
    registry = []
    def figure(rows=1, cols=1, height=2.8, ratios=None):
        kwargs = {'width_ratios': ratios} if ratios is not None else {}
        return plt.subplots(rows, cols, figsize=(WIDTH, height), layout='constrained',
                             gridspec_kw=kwargs or None, squeeze=False)
    def save(fig, name, claim, source, caption):
        for axis in fig.axes:
            colorbar = getattr(axis, '_colorbar', None)
            if colorbar is not None and colorbar.solids is not None:
                colorbar.solids.set_rasterized(False)
        issues = audit_layout(fig)+audit_design(fig)
        if issues:
            raise RuntimeError(f'{name}: {issues}')
        export_figure(fig, str(out/name), formats=['svg', 'png'], dpi=300,
                      size_inches=tuple(fig.get_size_inches()), tight=False,
                      grayscale_preview=False)
        with Image.open(out/f'{name}.png') as color:
            color.convert('L').save(out/'_qa'/f'{name}_grayscale.png', dpi=(300,300))
        registry.append({'name': name, 'claim': claim, 'source': source,
                          'caption': caption, 'size_inches': list(fig.get_size_inches()),
                          'layout_issues': issues, 'dpi': 300})
        plt.close(fig)
    def panel_labels(axes):
        for i, ax in enumerate(axes.flat):
            ax.set_title(chr(97+i), loc='left', fontweight='bold')
    def legend(ax):
        ax.legend(loc='best', frameon=False)
    def profiles_at(law, time):
        d = trajectories[law]
        return (np.array([np.interp(time, d['times'], d['temperature'][:,i])
                          for i in range(len(d['s']))]),
                np.array([np.interp(time, d['times'], d['moisture'][:,i])
                          for i in range(len(d['s']))]))

    a = inputs.ambient
    first = a[a[:,0] <= 1800]
    fig, ax = figure(2, 1, 3.0)
    ax[0,0].plot(first[:,0]/60, first[:,1], color=COLORS[1])
    ax[1,0].plot(first[:,0]/60, first[:,2], color=COLORS[0])
    ax[0,0].set(ylabel='环境温度 / ℃', xlim=(0,30))
    ax[1,0].set(xlabel='时间 / min', ylabel='有效空气浓度 / (kg/kg)', xlim=(0,30))
    save(fig, 'raw_q1_ambient', '预热阶段环境同时升温增湿', '附件1.xlsx，0—1800s共31点',
         '前30分钟环境观测。两面板分别表示温度和题给有效空气浓度，连线为相邻观测的线性插值。')

    fig, ax = figure(height=2.9)
    dots = ax[0,0].scatter(a[:,1], a[:,2], c=a[:,0]/3600, s=12, cmap='viridis',
                           linewidths=0)
    fig.colorbar(dots, ax=ax[0,0], label='观测时间 / h')
    ax[0,0].set(xlabel='环境温度 / ℃', ylabel='有效空气浓度 / (kg/kg)')
    save(fig, 'raw_q2_environment', '启动段共变后环境接近稳定区', '附件1.xlsx全部241点',
         '全部环境观测的温度—浓度关系，颜色为观测时间；共变不表示因果关系。')

    tail = a[a[:,0] >= 10800]
    fig, ax = figure(1,2,2.65)
    for axis, column, color, label in zip(ax.flat, [1,2], COLORS[:2],
                                          ['环境温度 / ℃','有效空气浓度 / (kg/kg)']):
        axis.hist(tail[:,column], bins=8, color=color, edgecolor='white', linewidth=.4)
        axis.axvline(tail[:,column].mean(), color='#222222', ls='--', lw=1,
                      label='末1小时均值')
        axis.set(xlabel=label, ylabel='观测数')
        axis.ticklabel_format(axis='x', style='plain', useOffset=False)
        axis.xaxis.set_major_locator(plt.MaxNLocator(3))
        legend(axis)
    panel_labels(ax)
    save(fig, 'raw_q3_tail', '末小时波动范围较小但后续运行仍需假设', '附件1.xlsx，10800—14400s共61点',
         '末1小时61条观测的经验分布，虚线为均值；这是观测波动，不是长期运行的置信区间。')

    r = inputs.radius_data
    fig, ax = figure(height=2.6)
    smooth = np.linspace(0,259200,721)
    ax[0,0].plot(smooth/3600, inputs.radius(smooth, True)*100, color=COLORS[0], label='保形插值')
    ax[0,0].scatter(r[:,0]/3600, r[:,1], facecolors='white', edgecolors=COLORS[0],
                     s=10, linewidths=.6, label='实测半径')
    ax[0,0].set(xlabel='时间 / h', ylabel='半径 / cm', xlim=(0,72))
    legend(ax[0,0])
    save(fig, 'raw_q4_radius', '实测收缩逐渐进入约1.2cm的平台', '附件2.xlsx全部145点',
         '全部半径观测与PCHIP曲线。曲线只在观测的0—72小时内展示，不存在拟造的后续半径数据。')

    d = trajectories['q1']
    select = np.linspace(0,len(d['times'])-1,121,dtype=int)
    fig, ax = figure(1,2,2.8)
    for axis, values, cmap, label in zip(ax.flat,
             [d['temperature'][select],d['moisture'][select]],
             ['magma','viridis'], ['温度 / ℃','含水率 / (kg/kg)']):
        mesh = axis.pcolormesh(d['times'][select]/60,d['s']*2,values.T,
                               shading='nearest',cmap=cmap,rasterized=False)
        fig.colorbar(mesh,ax=axis,label=label)
        axis.set(xlabel='时间 / min',ylabel='物理半径 / cm')
    panel_labels(ax)
    save(fig, 'process_q1_fields', '热量与水分在预热阶段具有不同传播尺度',
         'q1_trajectory.npz，显示121个时间与81个径向样本',
         '预热温度场与含水率场。颜色范围分别标注；显示网格不替代求解网格。')

    d = trajectories['q23']
    ids = np.where(d['times'] <= 10800)[0]
    ids = ids[np.linspace(0,len(ids)-1,121,dtype=int)]
    diffusivity = properties(d['moisture'][ids],d['temperature'][ids],'q23')[3]
    fig, ax = figure(height=2.8)
    mesh = ax[0,0].pcolormesh(d['times'][ids]/3600,d['s']*2,np.log10(diffusivity).T,
                              shading='nearest',cmap='viridis')
    fig.colorbar(mesh,ax=ax[0,0],label='log10[D / (m²/s)]')
    ax[0,0].set(xlabel='时间 / h',ylabel='物理半径 / cm')
    save(fig, 'process_q2_diffusivity', '耦合物性使扩散系数随时间和位置变化',
         'q23_trajectory.npz及题给D(C,T)经验公式',
         '前3小时扩散系数场，色阶为以m²/s计的D的常用对数；由实际T、C逐点代入公式。')

    fig, ax = figure(height=2.8)
    for value, label, color, style in zip(
            [d['moisture'][:,0],d['moisture'][:,-1],d['mean']],
            ['中心（全域最大）','表面','环带加权平均'],COLORS,STYLES):
        ax[0,0].plot(d['times']/3600,value,label=label,color=color,ls=style)
    ax[0,0].axhline(.15,color='#444444',ls=':',lw=.9)
    ax[0,0].axvline(4,color='#999999',ls=':',lw=.8)
    ax[0,0].set(xlabel='时间 / h',ylabel='含水率 / (kg/kg)',ylim=(0,2.65))
    legend(ax[0,0])
    save(fig, 'process_q3_drying', '表面和均值提前变干，终点须由中心判定',
         'q23_trajectory.npz；均值由原求解网格计算',
         '固定半径的中心、表面和环带平均含水率。水平线为0.15；竖线为4小时实测环境结束位置。')

    d4 = trajectories['q4']
    ids = np.linspace(0,len(d4['times'])-1,181,dtype=int)
    rr = np.linspace(0,2,101)
    field = np.array([np.interp(rr/d4['radius_cm'][i],d4['s'],d4['moisture'][i],right=np.nan)
                       for i in ids])
    fig, ax = figure(height=2.8)
    mesh = ax[0,0].pcolormesh(d4['times'][ids]/3600,rr,field.T,shading='nearest',
                              cmap='viridis',vmin=0,vmax=2.55)
    ax[0,0].plot(d4['times'][ids]/3600,d4['radius_cm'][ids],color='#222222',lw=1)
    fig.colorbar(mesh,ax=ax[0,0],label='含水率 / (kg/kg)')
    ax[0,0].set(xlabel='时间 / h',ylabel='物理半径 / cm',ylim=(0,2.04))
    save(fig, 'process_q4_moving', '含水率场的物理支持域随半径收缩',
         'q4_trajectory.npz；固定物理位置插值，域外NaN',
         '收缩模型在固定物理坐标中的含水率场。黑线为药材表面，线外留白表示没有材料，不能解释为零含水率。')

    t1,c1 = profiles_at('q1',1800)
    fig, ax = figure(1,2,2.6)
    for axis,value,label,color in zip(ax.flat,[t1,c1],['温度 / ℃','含水率 / (kg/kg)'],
                                       [COLORS[1],COLORS[0]]):
        axis.plot(trajectories['q1']['s']*2,value,color=color)
        axis.set(xlabel='物理半径 / cm',ylabel=label)
    panel_labels(ax)
    save(fig, 'result_q1_profiles', '1800秒时中心仍湿而表面更热更干',
         'q1_trajectory.npz末时刻', '预热结束时温度与含水率径向剖面，中心和表面都由方程求解。')

    fig, ax = figure(1,2,2.9)
    for i,hour in enumerate([.5,1,2,3]):
        temp,c = profiles_at('q23',hour*3600)
        for axis,value in zip(ax.flat,[temp,c]):
            axis.plot(d['s']*2,value,color=COLORS[i],ls=STYLES[i],label=f'{hour:g} h')
    ax[0,0].set(xlabel='物理半径 / cm',ylabel='温度 / ℃')
    ax[0,1].set(xlabel='物理半径 / cm',ylabel='含水率 / (kg/kg)')
    legend(ax[0,1]);panel_labels(ax)
    save(fig, 'result_q2_profiles', '热场趋于均匀早于含水率场',
         'q23_trajectory.npz的0.5、1、2、3h',
         '四个代表时刻的温度与含水率剖面；题目要求的六个时刻完整数值另列于表。两面板使用相同颜色和线型表示时间。')

    conv = summary['spatial_convergence']
    nn = np.array([x['n'] for x in conv])
    duration = np.array([x['q23']['threshold_hours'] for x in conv])
    fig, ax = figure(1,2,2.75,ratios=[1.7,1])
    ax[0,0].plot(nn,duration,marker='o',color=COLORS[0])
    ax[0,0].set_xscale('log',base=2)
    ax[0,0].set_xticks(nn,[str(n) for n in nn])
    ax[0,0].set(xlabel='径向区间数 N',ylabel='题三阈值时间 / h')
    last = nn >= 320
    ax[0,1].plot(nn[last],duration[last],marker='s',color=COLORS[0])
    ax[0,1].set(xlabel='加密区间数 N',ylabel='局部时间 / h')
    ax[0,1].xaxis.set_major_locator(plt.MaxNLocator(3))
    ax[0,1].ticklabel_format(axis='y',style='plain',useOffset=False)
    panel_labels(ax)
    save(fig, 'result_q3_convergence', '粗网格会严重高估后期干燥时间',
         'summary.json/spatial_convergence',
         '不同网格的全域阈值时间，右图放大精细网格。停止准则为相邻加密的时间相对差小于0.1%，同时检查题一指定表格误差。')

    matrix = np.array([[next(x['time_hours'] for x in summary['crossed_ablation']
                             if x['law']==law and x['moving']==moving)
                        for moving in [False,True]] for law in ['q23','q4']])
    fig, ax = figure(height=2.45)
    axis = ax[0,0]
    axis.pcolormesh(np.arange(3),np.arange(3),matrix,cmap='Blues',vmin=0,vmax=matrix.max()*1.2,
                    edgecolors='white',linewidth=3)
    for i in range(2):
        for j in range(2):
            axis.text(j+.5,i+.5,f'{matrix[i,j]:.2f} h',ha='center',va='center',
                       color='white' if matrix[i,j]>matrix.max()*.6 else '#111111',fontsize=12)
    axis.set_xticks([.5,1.5],['固定半径','实测收缩'])
    axis.set_yticks([.5,1.5],['题二/三物性','题四物性'])
    axis.invert_yaxis()
    axis.set(xlabel='几何方案',ylabel='物性方案')
    save(fig, 'result_q4_ablation', '几何收缩的加速与物性改变的减速需要分开识别',
         'summary.json/crossed_ablation，四个独立确定性计算',
         '几何与物性的四组合阈值时间，数值以小时计。每格均给出数值，颜色仅辅助比较；不是统计重复或置信区间。')

    fig, ax = figure(height=2.65)
    axis = ax[0,0]
    axis.plot(d['s']*2,d['moisture'][-1],color=COLORS[0],label='严格达标整秒的径向场')
    axis.axhline(.15,color='#444444',ls='--',label='全域阈值0.15')
    axis.axhline(d['mean'][-1],color=COLORS[2],ls=':',label='此时环带平均')
    axis.set(xlabel='物理半径 / cm',ylabel='含水率 / (kg/kg)',ylim=(0,.17))
    legend(axis)
    save(fig, 'result_q3_endpoint', '平均值达标不能保证中心达标',
         'q23_trajectory.npz终点完整场与均值',
         '严格达标整秒的径向含水率；未舍入中心值略低于0.15，图中与阈值重合是显示精度所致。')

    (out/'figure-registry.json').write_text(json.dumps(registry,ensure_ascii=False,indent=2))
    html = '<!doctype html><meta charset="utf-8"><title>A题结果图</title>'
    html += '<style>body{max-width:1000px;margin:40px auto;font:16px sans-serif}img{width:100%}figure{margin:30px 0}</style>'
    for item in registry:
        html += f'<figure><h3>{item["claim"]}</h3><img src="{item["name"]}.png"><figcaption>{item["caption"]}</figcaption></figure>'
    (out/'图表面板.html').write_text(html)
    return registry


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-dir',type=Path,default=Path('data/附件'))
    parser.add_argument('--out',type=Path,default=Path('.'))
    args = parser.parse_args()
    build_figures(args.input_dir,args.out)
