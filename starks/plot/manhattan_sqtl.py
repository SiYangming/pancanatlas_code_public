import os
import sys
import pandas as pd
import numpy as np
import cPickle
import h5py

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils
import config

import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
#import seaborn as sns

import matplotlib.gridspec as gridspec
from adjustText import adjust_text

sys.path.append('/cluster/home/starks/git/tools-python/viz/'); import gwas
VER = 6

# Location of trans/cis dataframes
_DATA_DIR              = '/cluster/work/grlab/projects/TCGA/PanCancer/QTL_Analysis_results/analysis_10kset/2dmanhattan_information_v%d'%VER
_GENOTYPE_H5_PATH      = '/cluster/work/grlab/projects/TCGA/PanCancer/hdf5_10Kset/mergedFiles_clean.hdf5'

# Genetic "constants"
_CANCER_GENE_PATH      = '/cluster/work/grlab/projects/TCGA/PanCancer/annotation/gencodeV14.v7.pancan_subset.ensembleID.list'
_CELL_CYCLE_GENE_PATH  = '/cluster/work/grlab/projects/TCGA/PanCancer/annotation/biomart_go_cell_cycle_strictv4.txt'
_RNA_BINDING_GENE_PATH = '/cluster/work/grlab/projects/TCGA/PanCancer/annotation/biomart_go_rna_binding_mRNA.txt'
_CHRM_LEN_PATH         = '/cluster/work/grlab/projects/TCGA/PanCancer/genome/hg19_hs37d5/chr_sizes'
_ENSG_TRANSLATE_PATH   = '/cluster/work/grlab/projects/ICGC/annotation/gencode.v19.annotation.hs37d5_chr.gtf.lookup.pickle'


# Load data fxns
def _hotfix_trans_colnames(df):
    df.index.name = df.columns[0].replace('# ', '')
    df.columns = df.columns.tolist()[1:-1] + df.columns[-1].split()
    return

def load_data(trans_df_path, cis_df_path):
    assert os.path.exists(trans_df_path)
    assert os.path.exists(cis_df_path)
    trans_df = pd.read_csv(trans_df_path, sep='\t')
    if trans_df.columns[0].startswith('#'):
        cols = trans_df.columns.tolist()
        cols[0] = cols[0].replace('# ', '')
        trans_df.columns = cols
    trans_df = trans_df.set_index('gene-id(event)')
    trans_df['is_trans'] = True

    cis_df = pd.read_csv(cis_df_path, sep='\t')
    if cis_df.columns[0].startswith('#'):
        cols = cis_df.columns.tolist()
        cols[0] = cols[0].replace('# ', '')
        cis_df.columns = cols
    cis_df = cis_df.set_index('gene-id(event)')
    cis_df['is_trans'] = False

    assert cis_df.columns.equals(trans_df.columns)
    data = pd.concat((trans_df, cis_df))
    return data

def _load_chrm_lens():
    '''Dictionary mapping chrm 1-22 to lens (keys & values are floats)
    '''
    df = pd.read_csv(_CHRM_LEN_PATH, sep='\t', header=None, index_col=0)
    df = df.loc[np.arange(1,23).astype(str)]
    df.index = df.index.astype(float)
    df.iloc[:, 0] = df.iloc[:, 0].astype(float)
    return df.iloc[:, 0].to_dict()

def _load_ensg_to_gene():
    data = cPickle.load(open(_ENSG_TRANSLATE_PATH, 'r'))
    return data['ensembl2genename']

# Format plot fxns
def _format_ax(ax):
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    return

def _increase_margin(ax, factor=.01):
    ylim = list(ax.get_ylim())
    ylength = ylim[1] - ylim[0]
    ylim[0] = ylim[0] - ylength * factor
    ylim[1] = ylim[1] + ylength * factor
    ax.set_ylim(ylim)

    xlim = list(ax.get_xlim())
    ylength = xlim[1] - xlim[0]
    xlim[0] = xlim[0] - ylength * factor
    xlim[1] = xlim[1] + ylength * factor
    ax.set_xlim(xlim)
    return

def _add_barplot_ensg_labels(ax, x_data, y_data, text_data):
    texts = [ax.text(x,y,t) for x,y,t in zip(x_data, y_data, text_data)]
    adjust_text(texts, expand_text=(1.2, .5),
                autoalign='xy', force_text=0.9, ax=ax,
                arrowprops=dict(arrowstyle="->", color='r', lw=0.5))
    return

def plot_sqtl_hist(ax, data, thold=100, ax_text=None):
    col_data = data.loc[data['is_trans'], :].set_index('gene-id(mutation)').loc[:, ['pos_gt']]
    col_data.index = col_data.index.map(lambda x: str(x).split('.')[0])
    unq, cnt = np.unique(col_data['pos_gt'], return_counts=True)
    map_pos_gt_to_count = dict(zip(unq, cnt))
    col_data['pos_gt_count'] = col_data['pos_gt'].map(lambda x: map_pos_gt_to_count[x])
    col_data = col_data.drop_duplicates()

    # Stagger small bars
    small_mask = col_data['pos_gt_count'] < 200
    bars = ax.bar(col_data.loc[~small_mask, 'pos_gt'],
                  col_data.loc[~small_mask, 'pos_gt_count'],
                  width=ax.get_xlim()[1] / np.maximum(60, col_data.shape[0]),
                  edgecolor='black', linewidth=1)

    color = 'b' if len(bars) == 0 else bars[0].get_facecolor()
    small_bars = ax.bar(col_data.loc[small_mask, 'pos_gt'],
                        col_data.loc[small_mask, 'pos_gt_count'],
                        width=ax.get_xlim()[1] / np.maximum(60, col_data.shape[0]),
                        color=color,
                        edgecolor='black', linewidth=1)

    ax.set_ylim(top=ax.get_ylim()[1] * 1.25)
    to_write = col_data.loc[col_data['pos_gt_count'] > thold].reset_index()[['pos_gt', 'pos_gt_count', 'gene-id(mutation)']]
    if ax_text is None:
        ax_text = ax
    else:
        ax_text.set_ylim(ax.get_ylim())
        ax_text.set_xlim(ax.get_xlim())
        ax_text.scatter(to_write['pos_gt'].values, to_write['pos_gt_count'].values, s=1)
    _add_barplot_ensg_labels(ax_text, to_write['pos_gt'].values,
                                      to_write['pos_gt_count'].values,
                                      to_write['gene-id(mutation)'].map(lambda x: _ENSG_TO_GENE[x]).values)

    ax.set_ymargin(0.2)
    ax.set_ylabel('# sQTL', size = 15)
    ax.set_xticks([])
    ax.yaxis.set_ticks_position('left')
    yticks = [0, int(50 * round(float(cnt.max())/50))]
    ax.set_yticks(yticks)
    ax.set_yticklabels(yticks)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    return bars, to_write

def plot_events_hist(ax, data):
    isTrans = data.loc[:, 'snp_chrm'] != data.loc[:, 'event-chrm']
    unq, cnt = np.unique(data.loc[data['is_trans'], 'pos_pt'], return_counts=True)

    ax.hist(data.loc[data['is_trans'], 'pos_pt'], bins=data.shape[0]/40 , orientation='horizontal')
    ax.set_xlabel('# Events', size = 15)
    ax.set_yticks([])

    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.xaxis.set_ticks_position('bottom')
    mylims = ax.get_xlim()
    ax.set_xticks(mylims)
    return

def plot_manhattan(ax, data):
    '''Scatter plot gt-pt associations, scale to genome position.

    Adds pos_gt & pos_pt to dataframe
    '''

    if 'marker_color' in data:
        data['pos_gt'] = np.nan
        data['pos_pt'] = np.nan
        for c, sub in data.groupby('marker_color'):
            pos_gt, pos_pt = gwas.makeManhattanPlot2D(pv=sub.loc[:, 'nominalp-value'].astype(float).values,
                                                      pos_gt=sub.loc[:, ['snp_chrm', 'snp_pos']].astype(float).values,
                                                      pos_pt=sub.loc[:, ['event-chrm', 'event-pos1']].astype(float).values,
                                                      marker_color=c, chrm_lens=_CHRM_LENS,
                                                      color_chrms=True, return_pos=True,
                                                      ax=ax) #, tag = genesettag)#### better evpo
            data.loc[data['marker_color'] == c, 'pos_gt'] = pos_gt
            data.loc[data['marker_color'] == c, 'pos_pt'] = pos_pt
    else:
        pos_gt, pos_pt = gwas.makeManhattanPlot2D(pv=data.loc[:, 'nominalp-value'].astype(float).values,
                                                  pos_gt=data.loc[:, ['snp_chrm', 'snp_pos']].astype(float).values,
                                                  pos_pt=data.loc[:, ['event-chrm', 'event-pos1']].astype(float).values,
                                                  marker_color='b', chrm_lens=_CHRM_LENS,
                                                  color_chrms=True, return_pos=True,
                                                  ax=ax) #, tag = genesettag)#### better evpo
        data['pos_gt'] = pos_gt
        data['pos_pt'] = pos_pt

    ax.set_xticklabels(ax.get_xticklabels(), rotation = 90)
    ax.set_ylabel('Splice Event Position', size = 15)
    ax.set_xlabel(ax.get_xlabel(), size = 15)
    return

def plot_gene_tags(ax, data):
    ax.grid(False)
    ax.set_ymargin(0.2)
    ax.set_facecolor('white')

    cancer_ensg = np.loadtxt(_CANCER_GENE_PATH, dtype=str)
    cell_cycle_ensg = np.loadtxt(_CELL_CYCLE_GENE_PATH, usecols=[0], dtype=str, skiprows=1)
    rna_bind_ensg = np.loadtxt(_RNA_BINDING_GENE_PATH, usecols=[0], dtype=str, skiprows=1)

    col_data = data.set_index('gene-id(mutation)').loc[:, 'pos_gt']
    col_data.index = col_data.index.map(lambda x: str(x).split('.')[0])

    pos_cancer_tags = col_data.loc[col_data.index.intersection(cancer_ensg)].unique()
    pos_cell_cycle_tags = col_data.loc[col_data.index.intersection(cell_cycle_ensg)].unique()
    pos_rna_bind_tags = col_data.loc[col_data.index.intersection(rna_bind_ensg)].unique()

    ax.scatter(pos_cancer_tags,     [0]*pos_cancer_tags.size, label='Cancer')
    ax.scatter(pos_cell_cycle_tags, [1]*pos_cell_cycle_tags.size, label='Cell Cycle')
    ax.scatter(pos_rna_bind_tags,   [2]*pos_rna_bind_tags.size, label='RNA Bind')
    ax.axis('off')
    return

def plot_event_tags(ax, data):
    ax.grid(False)
    ax.set_xmargin(0.2)
    ax.set_facecolor('white')

    cancer_ensg = np.loadtxt(_CANCER_GENE_PATH, dtype=str)
    cell_cycle_ensg = np.loadtxt(_CELL_CYCLE_GENE_PATH, usecols=[0], dtype=str, skiprows=1)
    rna_bind_ensg = np.loadtxt(_RNA_BINDING_GENE_PATH, usecols=[0], dtype=str, skiprows=1)

    row_data = data.loc[:, 'pos_pt']
    row_data.index = row_data.index.map(lambda x: str(x).split('.')[0])

    pos_cancer_tags = row_data.loc[row_data.index.intersection(cancer_ensg)].unique()
    pos_cell_cycle_tags = row_data.loc[row_data.index.intersection(cell_cycle_ensg)].unique()
    pos_rna_bind_tags = row_data.loc[row_data.index.intersection(rna_bind_ensg)].unique()

    ax.scatter([0]*pos_cancer_tags.size, pos_cancer_tags)
    ax.scatter([1]*pos_cell_cycle_tags.size,pos_cell_cycle_tags)
    ax.scatter([2]*pos_rna_bind_tags.size, pos_rna_bind_tags)
    ax.axis('off')
    return

def _sort_by_cnc(mut_status):
    tss_index = mut_status.index.map(lambda x: x.split('-')[1])
    return mut_status.iloc[np.argsort(tss_index)]

def add_marker_color(df, pval_thold):
    assert 'mutloadPV' in df
    df['is_sig'] = np.logical_and(df['mutloadPV'] < pval_thold, df['mutloadBeta'] < 0)
    is_sig_lut = {True: plt.get_cmap('Dark2')(0), False: plt.get_cmap('Dark2')(1)}
    df['marker_color'] = df['is_sig'].apply(lambda x: is_sig_lut[x])
    return

_CHRM_LENS = _load_chrm_lens()
_ENSG_TO_GENE = _load_ensg_to_gene()

COLOR = True
SUBSET = False

if __name__ == '__main__':
    write = True

    trans_df_path = os.path.join(_DATA_DIR, 'transdataresults_test_v%d_mutloadtag.tsv'%VER)
    cis_df_path = os.path.join(_DATA_DIR, 'cisdataresults_test_v%d_mutloadtag.tsv'%VER)
    outdir = os.path.join(config.plot_dir, 'sqtl')
    if not os.path.exists(outdir): os.makedirs(outdir)
    df = load_data(trans_df_path, cis_df_path)


    # Create Gridspecs
    fig = plt.figure(figsize=(13,13))
    gs = gridspec.GridSpec(4, 3,
                           width_ratios=[9, 1, .5],
                           height_ratios=[.5, 1, 1, 9],
                           hspace=0.05, wspace=0.05)
    ax_tdots = plt.subplot(gs[0,0]); _format_ax(ax_tdots)
    ax_text = plt.subplot(gs[1,0]); _format_ax(ax_text)
    ax_top = plt.subplot(gs[-2,0]); _format_ax(ax_top)
    ax_mh = plt.subplot(gs[-1,0]); _format_ax(ax_mh)
    ax_right = plt.subplot(gs[-1,-2]); _format_ax(ax_right)
    ax_rdots = plt.subplot(gs[-1,-1]); _format_ax(ax_rdots)
    ax_legend = plt.subplot(gs[0, -1]); _format_ax(ax_legend)

    pval_thold = .05 / 1000
    df['is_sig'] = np.logical_and(df['mutloadPV'] < pval_thold, df['mutloadBeta'] < 0)
    if COLOR:
        is_sig_lut = {True: plt.get_cmap('Dark2')(0), False: plt.get_cmap('Dark2')(1)}
        df['marker_color'] = df['is_sig'].apply(lambda x: is_sig_lut[x])
    if SUBSET:
        df = df.loc[~df['is_sig']]

    plt.suptitle('Taken from: %s' %_DATA_DIR)
    plot_manhattan(ax_mh, df)
    assert 'pos_gt' in df
    assert 'pos_pt' in df

    _increase_margin(ax_mh, factor=.005)

    ax_top.set_xlim(ax_mh.get_xlim())
    ax_tdots.set_xlim(ax_mh.get_xlim())

    ax_right.set_ylim(ax_mh.get_ylim())
    ax_rdots.set_ylim(ax_mh.get_ylim())

    ax_text.axis('off')
    sqtl_hist_thold = 80
    _, labeled_gene_df = plot_sqtl_hist(ax_top, df, thold=sqtl_hist_thold, ax_text=ax_text)

    plot_gene_tags(ax_tdots, df)
    plot_events_hist(ax_right, df)
    plot_event_tags(ax_rdots, df)

    # Add legend -- cancer, cell cycle, rna_bind
    dot_handles, dot_labels = ax_tdots.get_legend_handles_labels()
    ax_legend.legend(dot_handles, dot_labels)
    ax_legend.axis('off')

    fn_out = os.path.join(outdir, 'manhattan_sqtl_events_thold_%d_v%d.png'%(sqtl_hist_thold, VER))
    if SUBSET:
        fn_out = os.path.join(outdir, 'manhattan_sqtl_events_thold_sig_only_%d_v%d.png'%(sqtl_hist_thold, VER))
    plt.savefig(fn_out, layout='tight', dpi=300)
    print "Writing to %s" %fn_out
    pdf_out = fn_out.replace('.png', '.pdf')
    print "Writing to %s" %pdf_out
    plt.savefig(pdf_out, layout='tight')
    plt.close()
    np.save(fn_out.replace('.png', '') + '_labeled_ensg.npy', labeled_gene_df['gene-id(mutation)'].values)

