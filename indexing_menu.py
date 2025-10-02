import os
import glob
import shutil
import streamlit as st
import subprocess
import xml.etree.ElementTree as ET
from messages import messages as mess
from dataIO import read_for_bestM, text2lattice, read_peak_indexing,\
                        change_inp_xml_indexing, read_lattices_from_xml, read_cntl_inp_xml

def read_cntl_inp_xml (path):
    # XMLファイルを読み込む
    tree = ET.parse(path)  # ファイル名を適宜変更
    root = tree.getroot()

    # 各要素の取得
    control_param = root.find('.//ControlParamFile')
    control_param_file = control_param.text.strip() if control_param is not None else None

    peakdata_file = root.find('.//PeakDataFile')
    peakdata_file_name = peakdata_file.text.strip() if peakdata_file is not None else None

    outfile = root.find('.//OutputFile')
    outfile_name = outfile.text.strip() if outfile is not None else None
    return control_param_file, peakdata_file_name, outfile_name

class IndexingMenu:
    def __init__(self,):
        os.makedirs ('input', exist_ok = True)
        os.makedirs ('result', exist_ok = True)

        self.work = 'work_indexing'
        self.work_output = 'work_indexing/output'
        self.cntl_path = 'work_indexing/cntl.inp.xml'
        self.mess = mess['eng']
        self.param_path = 'input/param.inp.xml'
        self.param_path_idx = None
        self.peak_path = 'result/peakdata.txt'
        self.peak_path_idx = None
        self.log_path = 'result/LOG_CONOGRAPH.txt'
        self.log_path_idx = 'work_indexing/LOG_CONOGRAPH.txt'
        self.result_path = 'result/result.xml'
        self.result_path_idx = None
        self.selected_igor_path = 'result/selected.histogramIgor'
        self.output_zip_path = 'result/output.zip'
        self.path_exe = 'Conograph.exe'
        self.path_zip = 'work_indexing/archive.zip'
        self.lattice_eng2jpn = {
            'Cubic(F)' : '立方晶(F)',
            'Cubic(I)' : '立方晶(I)',
            'Cubic(P)' : '立方晶(P)',
            'Hexagonal' : '六方晶',
            'Rhombohedral' : '三方晶',
            'Tetragonal(I)' : '正方晶(I)',
            'Tetragonal(P)' : '正方晶(P)',
            'Orthorhombic(F)' : '斜方晶(F)',
            'Orthorhombic(I)' : '斜方晶(I)',
            'Orthorhombic(C)' : '斜方晶(C)',
            'Orthorhombic(P)' : '斜方晶(P)',
            'Monoclinic(P)' : '単斜晶(P)',
            'Monoclinic(A)' : '単斜晶(A)',
            'Monoclinic(B)' : '単斜晶(B)',
            'Monoclinic(C)' : '単斜晶(C)',
            'Triclinic' : '三斜晶'}
        
        self.lattice_jpn2eng = {
            v : k for k,v in self.lattice_eng2jpn.items()}
        
        self.cvtTbl = {'eng' : self.lattice_jpn2eng,
                       'jpn' : self.lattice_eng2jpn}
        
        self.outputLatticeDict = {
            'tric'    : 'OutputTriclinic',
            'monoc_P' : 'OutputMonoclinicP',
            'monoc_A' : 'OutputMonoclinicA',
            'monoc_B' : 'OutputMonoclinicB',
            'monoc_C' : 'OutputMonoclinicC',
            'ortho_P' : 'OutputOrthorhombicP',
            'ortho_C' : 'OutputOrthorhombicC',
            'ortho_I' : 'OutputOrthorhombicI',
            'ortho_F' : 'OutputOrthorhombicF',
            'tetra_P' : 'OutputTetragonalP',
            'tetra_I' : 'OutputTetragonalI',
            'rhombo'  : 'OutputRhombohedral',
            'hexago'  : 'OutputHexagonal',
            'cubic_P' : 'OutputCubicP',
            'cubic_I' : 'OutputCubicI',
            'cubic_F' : 'OutputCubicF' }
        self.bravais = None
        self.set_files ()

    def set_files (self,):
        p_path, h_path, out_path = read_cntl_inp_xml (
                                                self.cntl_path)
        self.param_path_idx = os.path.join (self.work, p_path)
        self.peak_path_idx = os.path.join (self.work, h_path)
        self.result_path_idx = self.work + '/' + out_path

    def set_language (self,):
        if st.session_state['lang'] is not None:
            lang = st.session_state['lang']
            st.session_state['mess_idx'] = mess[lang]['indexing']

    def read_session (self,):
        params = st.session_state['params_idx']
        mes = st.session_state['mess_idx']
        return mes, params

    def params2text (self, params):
        text = []
        for k,v in params.items():
            text.append (k + ' / ' + v)
        ans = '\n'.join (text)
        return ans

    def display_param (self,):
        lang = st.session_state['lang']
        params = st.session_state['params_idx_defau']
        
        if st.toggle (
            {'eng' : 'Show Default Parameter (Indexing)',
            'jpn' : 'パラメータ初期値 表示 (Indexing)'}[lang],
            key = 'display_default_param_indexing'):
            text = self.params2text (params)
            st.write (text)
    
    def exec_indexing (self, ):
        lang = st.session_state['lang']
        if st.button ({'eng' : 'Indexing Run',
                       'jpn':'Indexing実行'}[lang]):
            res = self.exec_cmd ('quit\n')
            st.session_state['list_candidates'] = None
            if os.path.exists (self.result_path_idx):
                shutil.copyfile (self.result_path_idx, self.result_path)

            return res
        
        return None
    
    def exec_cmd (self, cmd):
        shutil.copyfile (self.param_path, self.param_path_idx)
        shutil.copyfile (self.peak_path, self.peak_path_idx)
        shutil.rmtree (self.work_output)
        os.makedirs (self.work_output)
        cwd = os.getcwd ()
        os.chdir (self.work)
        result = subprocess.run(
                        [self.path_exe], input = cmd,
                        capture_output = True, text = True)    
        os.chdir (cwd)
        return result

    def take_indexing_peak_data (self, numCandidate):
        cmd = numCandidate + '\nquit\n'
        res = self.exec_cmd (cmd)
        path = glob.glob (self.work_output + '/sample_lattice(*).histogramIgor')[0]
        shutil.copyfile (path, self.selected_igor_path)
        selected_lat_peak = read_peak_indexing (self.selected_igor_path)
        st.session_state['peakDf_indexing'] = selected_lat_peak

    def take_indexing_peak_data_selected (self,):
        lang = st.session_state['lang']
        result = st.session_state['result'][lang]
        numCandidate = result['lattice_selected']['number']
        st.session_state['list_candidates'] = [numCandidate]
        self.take_indexing_peak_data (numCandidate)

    def get_fname (self, res):
        fname = res.headers.get ('file_name')
        fname = fname.split('/')[-1]
        return fname

    def request_log (self,):
        ans = None
        if os.path.exists (self.log_path_idx):
            shutil.copyfile (self.log_path_idx, self.log_path)
            ans = 'Done'
        
        return ans

    def search_level (self, params_dict):
        mes, params = self.read_session ()

        selDefault = int (params['SearchLevel'])
        nPeakDefault = params['MaxNumberOfPeaks']
        
        sel1 = mes['quickSearch']
        sel2 = mes['deepSearch']
        select = st.radio (mes['level'],
                           [sel1, sel2], horizontal = True,
                           index = selDefault)
        nPeak = st.text_input (mes['nPeak'], nPeakDefault)

        select = {sel1 : '0', sel2 : '1'}[select]
        params_dict['SearchLevel'] = select
        params_dict['MaxNumberOfPeaks'] = nPeak

        return params_dict
        
    def search_method (self, params_dict):
        mes, params = self.read_session ()
        selDef = int (params['IsAngleDispersion'])
        sel1 = mes['tof']; sel2 = mes['angleDisp']
        sel = st.radio (mes['select'],
                        [sel1, sel2], index = selDef,
                        horizontal = True)
        
        params_dict['IsAngleDispersion'] = {
            sel1 : '0', sel2 : '1'}[sel]
        
        ps_dafau = st.session_state['params_idx_defau']
        
        if sel == sel1:
            st.write (
                'TOF = c0+c1d+c2d^2+c3d^3+c4d^4+c5d^5')
            col1, col2, col3 = st.columns (3)
            convParams = params['ConversionParameters']

            if len (convParams) > 0: 
                ps = convParams.strip().split (' ')
            else: ps = [' ',' ',' ']
            
            with col1: p1 = st.text_input (
                'v1', ps[0], key = 'conv1',
                label_visibility = 'collapsed')
            with col2: p2 = st.text_input (
                'v2', ps[1], key = 'conv2',
                label_visibility = 'collapsed')
            with col3: p3 = st.text_input (
                'v3', ps[2], key = 'conv3',
                label_visibility = 'collapsed')

            ans = ' '.join ([p1, p2, p3])

            params_dict['ConversionParameters'] = ans
            params_dict['WaveLength'] = ps_dafau['WaveLength']
            params_dict['ZeroPointShiftParameter'] = ps_dafau['ZeroPointShiftParameter']
            
        else:
            col1, col2 = st.columns (2)
            with col1:
                waveLen = st.text_input (
                                mes['waveLen'],
                                params['WaveLength'])
            with col2:
                zeroPoint = st.text_input (
                        mes['zeroPoint'],
                        params['ZeroPointShiftParameter'])
            
            params_dict['WaveLength'] = waveLen
            params_dict['ZeroPointShiftParameter'] = zeroPoint
            params_dict['ConversionParameters'] = ' '

        return params_dict
            
    def nPeakForM (self, params_dict):
        mes, params = self.read_session ()
        nPeak = params['MaxNumberOfPeaksForFOM']
        
        ans = st.text_input (mes['nPeakForM'], nPeak)

        params_dict['MaxNumberOfPeaksForFOM'] = ans

        return params_dict

    def min_max_miller_idx (self, params_dict):
        mes, params = self.read_session ()
        message = mes['minMaxPeak']
        minN = params['MinNumberOfMillerIndicesInRange']
        maxN = params['MaxNumberOfMillerIndicesInRange']
        st.write (message)
        col1, col2 = st.columns (2)
        with col1:
            minIdx = st.text_input ('min :', minN, key = 'min')
        with col2:
            maxIdx = st.text_input ('max :', maxN, key = 'max')

        params_dict['MinNumberOfMillerIndicesInRange'] = minIdx
        params_dict['MaxNumberOfMillerIndicesInRange'] = maxIdx

        return params_dict

    def minFOM (self, params_dict):
        mes, params = self.read_session ()        
        message = mes['minFOM']
        param = params['MinFOM']
        ans = st.text_input (message, param)

        params_dict['MinFOM'] = ans
        return params_dict

    def rangeLattice (self, params_dict):
        mes, params = self.read_session ()
        message = mes['rangeLattice']
        minRange = params['MinUnitCellEdgeABC']
        maxRange = params['MaxUnitCellEdgeABC']
        st.write (message)
        col1, col2 = st.columns (2)
        with col1:
            minV = st.text_input ('min', minRange, key = 'minRange')
        with col2:
            maxV = st.text_input ('max', maxRange, key = 'maxRange')
        
        params_dict['MinUnitCellEdgeABC'] = minV
        params_dict['MaxUnitCellEdgeABC'] = maxV
        return params_dict

    def resolution_err (self, params_dict):
        mes, params = self.read_session ()
        message = mes['resolution']
        param = params['Resolution']
        ans = st.text_input (message, param)
        params_dict['Resolution'] = ans

        return params_dict

    def select_lattice_pattern (self, params_dict):
        lang = st.session_state['lang']
        st.write ({
            'eng' : 'Output lattice pattern selection',
            'jpn' : '出力格子パターンの選択＞＞'}[lang])
        mes, params = self.read_session ()
        axisMonocliSym = params['AxisForMonoclinicSymmetry'].strip()
        monocABC = 'monoc_' + axisMonocliSym
        lattices = ['tric', 'monoc_P', monocABC,
                    'ortho_P', 'ortho_C', 'ortho_I', 'ortho_F',
                    'tetra_P', 'tetra_I', 'rhombo', 'hexago',
                    'cubic_P', 'cubic_I', 'cubic_F']
        
        cols = st.columns (2)
        for i, pattern in enumerate (lattices):
            label = mes[pattern]
            nameOut = self.outputLatticeDict[pattern]
            defV = params[nameOut].strip() == '1'
            with cols[i // 7]:
                state = st.checkbox (label = label,
                            key = 'chk_{}'.format(i), value = defV)
                params_dict[nameOut] = str (int (state))

        return params_dict

    def params_precision_search (self, params_dict):
        lang = st.session_state['lang']
        st.write (
            {'eng' : '＜＜Parameters for precise indexing＞＞',
            'jpn' : '＜＜指標付け詳細パラメータ＞＞'}[lang])
        
        mes, params = self.read_session ()
        param_1_1 = params['MinPrimitiveUnitCellVolume']
        param_1_2 = params['MaxPrimitiveUnitCellVolume']
        param_2 = params['MaxNumberOfTwoDimTopographs']
        param_3 = params['MaxNumberOfLatticeCandidates']
        param_4 = params['CriticalValueForLinearSum']
        param_5 = params['ThresholdOnNormM']
        param_6 = params['ThresholdOnRevM']
        param_7 = params['MinDistanceBetweenLatticePoints']
        if 'MaxNumberOfSolutionsForEachBravaisLattice' in params:
            param_8 = params['MaxNumberOfSolutionsForEachBravaisLattice']
        else: param_8 = None
        
        mes1 = mes['threshPrim']
        st.write (mes1)
        col1_1, col1_2 = st.columns (2)
        with col1_1:
            minPrimeCellV = st.text_input ('min', param_1_1, key = '1_1')
        with col1_2:
            maxPrimeCellV = st.text_input ('max', param_1_2, key = '1_2')

        mes2 = mes['maxNumZone']
        maxNumZone = st.text_input (mes2, param_2, key = '2')

        mes3 = mes['numPrimCell']
        numPrimCell = st.text_input (mes3, param_3, key = '3')
        
        mes4 = mes['v4linearSum']
        errQvalue = st.text_input (mes4, param_4, key = '4')

        mes5 = mes['minMwu']
        minMwu = st.text_input (mes5, param_5, key = '5')

        mes6 = mes['minMrev']
        minMrev = st.text_input (mes6, param_6, key = '6')

        mes7 = mes['minDistPoints']
        minDistPoints = st.text_input (mes7, param_7, key = '7')
        
        if param_8 is not None:
            mes8 = mes['maxLatticeConst']
            maxLatticeConst = st.text_input (mes8, param_8, key = '8')
        else: maxLatticeConst = None

        params_dict[
            'MinPrimitiveUnitCellVolume'] = minPrimeCellV
        params_dict[
            'MaxPrimitiveUnitCellVolume'] = maxPrimeCellV
        params_dict[
            'MaxNumberOfTwoDimTopographs'] = maxNumZone
        params_dict[
            'MaxNumberOfLatticeCandidates'] = numPrimCell
        params_dict[
            'CriticalValueForLinearSum'] = errQvalue
        params_dict[
            'ThresholdOnNormM'] = minMwu
        params_dict[
            'ThresholdOnRevM'] = minMrev
        params_dict[
            'MinDistanceBetweenLatticePoints'
                                        ] = minDistPoints
        if maxLatticeConst is not None:       
            params_dict[
                'MaxNumberOfSolutionsForEachBravaisLattice'
                                        ] = maxLatticeConst
        
        return params_dict
    
    def to_jpn (self, eng):
        if eng not in self.lattice_eng2jpn:
            return eng
        return self.lattice_eng2jpn[eng] 

    # bestM, lattice constant, lattice selected, lattice candidatesの
    # 結果を和英両方を設定
    def put_result_jpn_eng (self,
            df_bestM, txt_bestM, dict_bestM, latConst,
            lattice_selected, lattice_candidates):
        
        eng = { 'df_bestM' : df_bestM, 'txt_bestM' : txt_bestM,
                'dict_bestM' : dict_bestM, 'latConst' : latConst,
                'lattice_selected' : lattice_selected,
                'lattice_candidates' : lattice_candidates }
        
        df_jp = df_bestM.copy()
        df_jp['CrystalSystem'] = df_jp[
                            'CrystalSystem'].apply (self.to_jpn)
        txt_jp = []
        for txt in txt_bestM:
            t1, t2 = txt.split (':')
            t1 = t1.strip(); t2 = t2.strip()
            txt_jp.append (' : '.join ([self.to_jpn (t1), t2]))
        
        dict_jp = {
            self.to_jpn (k) : v for k, v in dict_bestM.items()}
        lat_jp = latConst.copy()
        lat_jp['CrystalSystem'] = lat_jp[
            'CrystalSystem'].apply (self.to_jpn)

        sel_jp = lattice_selected
        sel_jp['CrystalSystem'] = self.to_jpn (sel_jp['CrystalSystem'])

        cand_jp = lattice_candidates.copy()
        cand_jp['CrystalSystem'] = cand_jp['CrystalSystem'].apply (self.to_jpn)

        jpn = {'df_bestM' : df_jp, 'txt_bestM' : txt_jp,
                'dict_bestM' : dict_jp, 'latConst' : lat_jp,
                'lattice_selected' : sel_jp,
                'lattice_candidates' : cand_jp}
        
        result = {'eng' : eng, 'jpn' : jpn}

        st.session_state['result'] = result 
    
    def get_result(self, res):
        ans = None  # ← これで常に定義済みにしておく

        if res is None:
            return ans  # None を返す

        shutil.copyfile (self.result_path_idx, self.result_path)
        df_bestM, txt_bestM, dict_bestM, candi_exists = read_for_bestM(self.result_path)
        latConst = text2lattice(dict_bestM)
        selected_lattice, lattice_candidates = read_lattices_from_xml(self.result_path)

        self.put_result_jpn_eng(
                    df_bestM, txt_bestM, dict_bestM, latConst,
                    selected_lattice, lattice_candidates)
        st.session_state['candidate_exist'] = candi_exists
        ans = candi_exists

        return ans


    # パラメータ設定メニュー
    def param_menu (self,):
        lang = st.session_state['lang']
        newParams = {}

        # toggleが選択されなければ、newParamsは空のまま
        # toggleが選択されれば、newParamsにはメニューで
        # 選択されたパラメータが入る
        with st.expander (
            {'eng' : 'Open parameter menu (Indexing)',
             'jpn' : 'パラメータメニュー (Indexing)'}[lang]):
            newParams = self.search_level (newParams)
            
            newParams = self.search_method (newParams)

            newParams = self.nPeakForM (newParams)

            newParams = self.min_max_miller_idx (newParams)

            newParams = self.minFOM (newParams)

            newParams = self.rangeLattice (newParams)

            newParams = self.resolution_err (newParams)

            newParams = self.select_lattice_pattern (newParams)

            newParams = self.params_precision_search (newParams) 

        return newParams

    def menu (self, ):
        if st.session_state['params_idx_defau'] is not None:
            #self.display_param ()
            
            with st.container (border = True):
                newParams = self.param_menu ()
                exec_space = st.empty ()

            if len (newParams) > 0:
                change_inp_xml_indexing (newParams, self.param_path)

            if os.path.exists (self.param_path) & os.path.exists (self.peak_path):
    
                with exec_space:
                    res = self.exec_indexing ()

                result = self.get_result (res)
                if isinstance (result, str):
                    st.write (res)

                elif result is not None:
                    if result:
                        self.take_indexing_peak_data_selected ()
                        st.session_state['menu_indexing'] = True
                        st.session_state['menu_peaksearch'] = False

                    else:
                        st.session_state['peakDf_indexing'] = None
                        st.session_state['menu_indexing'] = True
                        st.session_state['menu_peaksearch'] = False

    def disp_bestM (self,):
        lang = st.session_state['lang']
        result = st.session_state['result'][lang]
        df_bestM = result['df_bestM']
        txt_bestM = result['txt_bestM']
        dict_bestM = result['dict_bestM']
        st.table (df_bestM)
        sel = st.selectbox (
            {'eng' : 'Select Bravais Lattice..',
            'jpn' : 'ブラベー格子の選択'}[lang],
            txt_bestM)
        sel = sel.split(':')[0].strip()
        col1, col2 = st.columns (2)
        with col1:
            st.write (
                {'eng' : 'Selected Bravais lattice : ',
                 'jpn' : '選択されたブラベー格子 : '}[lang])
        with col2:
            st.write (sel)

        text = dict_bestM[sel]
        text = text.replace ('\n', '  \n')
        st.markdown (text)

    def disp_lattice_consts (self,):
        lang = st.session_state['lang']
        result = st.session_state['result'][lang]
        df = result['latConst']
        st.table (df)

    def to_float (self, vstr):
        if vstr == '-': return vstr
        return str (float (vstr))

    def build_candidate_df (self,):
        lang = st.session_state['lang']
        df = st.session_state['result'][lang]['lattice_candidates']
        df = df.rename (
            columns = {
                'FigureOfMeritWolff' : 'M',
                'FigureOfMeritWu' : 'Mwu',
                'ReversedFigureOfMeritWolff' : 'Mrev',
                'SymmetricFigureOfMeritWolff' : 'Msym',
                'NumberOfLatticesInNeighborhood' : 'NN',
                })
        
        df['M'] = df['M'].apply (self.to_float)
        df['Mwu'] = df['Mwu'].apply (self.to_float)
        df['Mrev'] = df['Mrev'].apply (self.to_float)
        df['Msym'] = df['Msym'].apply (self.to_float)
        df['OptimizedParameters'] = df['OptimizedParameters'].apply (
            lambda ps: ', '.join ([self.to_float(p) for p in ps.split()]))

        values = df.loc[:, ['M', 'Mwu', 'Mrev', 'Msym', 'NN',
                     'OptimizedParameters']].values
        values = [', '.join (vs[:-1]) + '; ' + vs[-1] for vs in values]
        
        df['for_menu'] = values
        if df['M'].unique()[0] != '-':
            df['M'] = df['M'].apply (float)

        return df

    def menu_select_candidate (self,):
        lang = st.session_state['lang']
        css = {'eng' : list (self.lattice_eng2jpn.keys()),
                'jpn' : list (self.lattice_eng2jpn.values())}[lang]

        df = self.build_candidate_df ()
        text = 'M, Mwu, Mrev, Msym, NN; a, b, c, α, β, γ'
        st.write ({'eng' : 'Bravais lattice  : ',
                'jpn' : 'ブラベー格子 : '}[lang] + text)
        
        numSelectedCandidate =\
            st.session_state['result'][lang]['lattice_selected']['number']
        
        for cs in css:
            params = df.loc[df['CrystalSystem'] == cs]
            if len (params) == 0:
                st.write (cs)
            else:
                params = params.sort_values('M', ascending = False)
                sels = params['for_menu'].tolist()
                nums = params['number'].tolist()
                sel_dict = {sel  : num for sel, num in zip (sels, nums)}

                sels = ['-----'] + sels

                if numSelectedCandidate in nums: idx = 1
                else: idx = 0

                sel = st.selectbox (cs, sels, index = idx, # = idx
                                    key = cs)
                
                self.manage_list_candidates (sel, sel_dict)
        
        if (st.session_state['list_candidates'] is not None) and (len (st.session_state['list_candidates']) > 1):
            selected_num = st.session_state['list_candidates'][-1]
            if selected_num != numSelectedCandidate:
                self.take_indexing_peak_data (selected_num)

    def operation_summary (self,):
        lang = st.session_state['lang']
        flg = st.button (
            {'eng' : 'Get histogramIgor files after refinement...',
             'jpn' : '細密化されたhistogramIgorファイルの入手'}[lang])
        if flg:
            res = self.exec_summary ()
            self.download_output (res)

    def exec_summary (self,):
        cmd = st.session_state['list_candidates']
        cmd = '\n'.join (cmd) + '\nquit\n'
        res = self.exec_cmd (cmd)
        shutil.make_archive (self.output_zip_path.replace ('.zip', ''), format = 'zip',
                            root_dir = self.work_output)

        if os.path.exists (self.output_zip_path):
            return 'Done'
        else:
            return '送信ファイルがありません'
        
    def download_output (self, res):
        if res == 'Done':
            lang = st.session_state['lang']
            with open (self.output_zip_path, 'rb') as f:
                zip_file = f.read()

            st.download_button (
                {'eng' : 'Download data',
                 'jpn' : 'ダウンロードデータ'}[lang],
                data = zip_file,
                file_name = self.output_zip_path
            )

    def manage_list_candidates (self, sel, sel_dict):
        nums = list (sel_dict.values())

        list_candidates = st.session_state['list_candidates']
        selected_num = list_candidates.pop (0)

        list_candidates = [n for n in list_candidates if n not in nums]
        
        if sel != '-----':
            list_candidates.append (sel_dict[sel])            

        list_candidates = [selected_num] + list_candidates
        st.session_state['list_candidates'] = list_candidates

    def display_log (self,):
        with open (self.log_path, 'r', encoding = 'utf-8') as f:
            text = f.read()
        st.text_area ('log', text, height = 400)

if __name__ == '__main__':
    shutil.make_archive ('archive', format= 'zip',
                        root_dir = 'work_indexing/output')
    #from init import setup_session_state
    #setup_session_state ()
    #idx = IndexingMenu ()
