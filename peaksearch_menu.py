import os
import shutil
import streamlit as st
import subprocess
from messages import messages as mess
from dataIO import change_inp_xml, read_histo_file, read_cntl_inp_xml

class PeakSearchMenu:
    def __init__ (self, ):
        os.makedirs ('input', exist_ok = True)
        os.makedirs ('result', exist_ok = True)

        self.work = 'work_peaksearch'
        self.pathSample = 'sample'
        self.param_path = 'input/param.inp.xml'
        self.param_path_pk = None
        self.hist_path = 'input/histogram.txt'
        self.hist_path_pk = None
        self.out_path = 'result/peakdata.txt'
        self.out_path_pk = None
        self.log_path = 'result/LOG_PEAKSEARCH.txt'
        self.log_path_pk = 'work_peaksearch/LOG_PEAKSEARCH.txt'
        self.path_cntl = 'work_peaksearch/cntl.inp.xml'
        self.set_files ()
        self.path_exe = 'PeakSearch.exe'

    def set_files (self,):
        p_path, h_path, out_path = read_cntl_inp_xml (self.path_cntl)
        self.param_path_pk = os.path.join (self.work, p_path)
        self.hist_path_pk = os.path.join (self.work, h_path)
        self.out_path_pk = os.path.join (self.work, out_path)

    def set_language (self,):
        if st.session_state is not None:
            lang = st.session_state['lang']
            st.session_state['mess_pk'] = mess[lang]['peaksearch']
            st.session_state['mess_gr'] = mess[lang]['graph']
        
    def display_log (self,):
        with open (self.log_path, 'r', encoding = 'utf-8') as f:
            text = f.read()
        st.text_area ('log', text, height = 400)

    def load_files (self,):
        param_name = st.session_state['param_name']
        hist_name = st.session_state['hist_name']

        uploaded_map = {}
        with open (self.param_path, 'rb') as f:
            uploaded_map[param_name] = f.read()
        with open (self.hist_path, 'rb') as f:
            uploaded_map[hist_name] = f.read ()
        return uploaded_map

    def display_param (self, params):
        lang = st.session_state['lang']
        if st.toggle (
            {'eng' : 'Show Default Parameter (Peaksearch)',
            'jpn' : 'パラメータ初期値 表示 (ピークサーチ)'}[lang],
            key = 'display_default_param_pksearch'):
            text = self.params2text (params)
            st.write (text)

    def exec_peaksearch (self,):
        lang = st.session_state['lang']

        if st.button ({'eng' : 'Peaksearch Exec',
                       'jpn':'ピークサーチ実行'}[lang]):
            
            shutil.copyfile (self.param_path, self.param_path_pk)
            shutil.copyfile (self.hist_path, self.hist_path_pk)

            cwd = os.getcwd ()
            os.chdir (self.work)
            subprocess.run ([self.path_exe])
            os.chdir (cwd)
            
            return 'Done'

        return None

    def request_log (self,):
        ans = None

        if os.path.exists (self.log_path_pk):
            shutil.copyfile (self.log_path_pk, self.log_path)
            ans = self.log_path
        else:
            ans = 'Error 500'
    
        return ans

    def edit_table_peak (self, peakDf):
        lang = st.session_state['lang']
        mess_gr = st.session_state['mess_gr']
        dispDf = peakDf
        dispDf.columns = [
            {'eng' : 'Peak', 'jpn' : 'ピーク'}[lang],
                mess_gr['pos'], mess_gr['peakH'],
                mess_gr['fwhm'], mess_gr['sel']]

        edited_df = st.data_editor (
            dispDf,
            column_config = {
                mess_gr['sel']: st.column_config.CheckboxColumn(
                            mess_gr['sel'], default = True)},
            use_container_width = True)
        edited_df = edited_df.rename (columns = {mess_gr['sel'] : 'Flag'})
        return edited_df

    def feedbackSelectedPeakToFile (self, selected):
        selected['Flag'] = selected['Flag'].apply (lambda x: str (int (x)))
        with open (self.out_path, 'r', encoding = 'utf-8') as f:
            lines = f.readlines ()

        st = None; ed = None; flg = False
        for i, line in enumerate (lines):
            if 'WAVES/O peak, peakpos, height, FWHM, Flag' in line:
                flg = True
            elif flg & ('BEGIN' in line):
                st = i + 1

            if st is not None:
                for j in range (i + 1, len (lines)):
                    if 'END' in lines[j]: break
                    ed = j
            
                break

        lines_1, lines_2 = lines[:st], lines[ed + 1:]

        new_lines = []
        cols = selected.columns
        for _, row in selected.iterrows():
            vs = [row[col] for col in cols]
            vs = [str (int (vs[0])), f"{vs[1]:.6e}",
                  f"{vs[2]:.6e}", f"{vs[3]:.6e}", vs[4]]
            vs = '{:>5}{:>15}{:>15}{:>15}{:>5}'.format (*vs) 
            new_lines.append (vs + '\n')
        ans = lines_1 + new_lines + lines_2

        ans = ''.join (ans)
        with open (self.out_path, 'w', encoding = 'utf-8') as f:
            f.write (ans)

    def smthParams (self, params):
        mess_pk = st.session_state['mess_pk']
        st.write (mess_pk['smth_mes'])
        col1,col2 = st.columns (2)
        nPointsDefault = params['nPoints']
        endRegionDefault = params['endRegion'] 
        with col1:
            nPoints = st.text_input (
                mess_pk['tbl_col1'],
                nPointsDefault)
        with col2:
            endRegion = st.text_input (
                mess_pk['tbl_col2'],
                endRegionDefault)
            
        return nPoints, endRegion
    
    def rangeParam (self, params):
        mess_pk = st.session_state['mess_pk']
        st.write (mess_pk['area_mes'])
        col1,col2 = st.columns (2)
        rangeMin, rangeMax = params['minRange'], params['maxRange']
        if rangeMin == 'MIN': rangeMin = 0.0
        with col1:
            minRange = st.text_input ('min', rangeMin)
        with col2:
            maxRange = st.text_input ('max', rangeMax)

        return minRange, maxRange
    
    def thresholdParam (self, params):
        mess_pk = st.session_state['mess_pk']
        lang = st.session_state['lang']
        st.write (mess_pk['th_mes'])
        col1, col2 = st.columns ([2,8])
        c_def = params['c_fixed']
        useErrDict = {
            1 : mess_pk['th_sel_1'],
            0 : mess_pk['th_sel_2']}
        
        with col1:
            c_fixed = st.text_input ('c : ', c_def)
        
        with col2:
            use_error = st.selectbox (
                {'eng' : 'select','jpn' : '選択'}[lang],
                options = list (useErrDict.values()))

        return c_fixed, use_error

    def kalpha2Select (self,):
        mess_pk = st.session_state['mess_pk']
        yes = mess_pk['exec_sel_1']
        no = mess_pk['exec_sel_2']
        select = st.radio (mess_pk['delpk_mes'],
                           [yes, no], horizontal = True)
        return select

    def kalpha2Param (self, params):
        lang = st.session_state['lang']
        mess_pk = st.session_state['mess_pk']
        kalpha1, kalpha2 = params['kalpha1'], params['kalpha2']

        noSel = {'jpn' : '選択', 'eng' : 'Select'}[lang]
        params = [
            noSel,
            'Ag / 0.5594075 / 0.563798',
            'Mo / 0.709300 / 0.713590',
            'Cu / 1.540562 / 1.544398',
            'Co / 1.788965 / 1.792850',
            'Fe / 1.936042 / 1.939980',
            'Cr / 2.289700 / 2.293606']
        
        col1, col2, col3 = st.columns (3)
        with col3:
            sel = st.selectbox (
                mess_pk['wavelen_mes'], params, index = 0)

        if sel != noSel:
            kalpha1 = kalpha1, kalpha2 = sel.split (' / ')[1:]
            
        with col1: kalpha1 = st.text_input ('Kα1', kalpha1)
        with col2: kalpha2 = st.text_input ('Kα2', kalpha2)

        return kalpha1, kalpha2


    def operationParam (self, params, savePath):
        defParams = st.session_state['params']
        mess_pk = st.session_state['mess_pk']
        minRange = params['minRange'] #; maxRange = params['maxRange']
        useErr = params['useErr']
        select = params['select']
        kalpha1 = params['kalpha1']; kalpha2 = params['kalpha2']
        if str (minRange) == '0.0': params['minRange'] = 'MIN'
        params['useErr'] = int (useErr == mess_pk['th_sel_1'])
        params['select'] = int (select == mess_pk['exec_sel_1'])
        if (kalpha1 == None) | (kalpha2 == None):
            params['kalpha1'] = defParams['kalpha1']
            params['kalpha2'] = defParams['kalpha2']
        change_inp_xml (params, savePath)

    def params2text (self, params):
        lang = st.session_state['lang']
        mess_pk = st.session_state['mess_pk']
        text = ''
        nPoints = params['nPoints']
        endRegion = params['endRegion']
        range_begin, range_end = params['minRange'], params['maxRange']
        threshold, useErr = params['c_fixed'], params['useErr']
        alpha2_correction = params['select']
        kalpha1, kalpha2 = params['kalpha1'], params['kalpha2']

        text += {'eng':'Smoothing / ', 'jpn' : '平滑化 / '}[lang]
        text += mess_pk['tbl_col1'] + ' : {}, '.format (nPoints)
        text += mess_pk['tbl_col2'] + ' : {}  \n'.format (endRegion)

        text += mess_pk['area_mes'] + ' / '
        text += 'min : {}, max : {}  \n'.format (range_begin, range_end)
        text += {'eng':'threshold', 'jpn' : 'しきい値'}[lang] + ' / '
        text += 'c : {}, '.format (threshold)
        text += {0 : mess_pk['th_sel_2'],
                 1 : mess_pk['th_sel_1']
                 }[int (useErr)] + '  \n'

        text += mess_pk['delpk_mes'] + ' / '
        text += {0 : mess_pk['exec_sel_2'],
                 1 : mess_pk['exec_sel_1']
                 }[int (alpha2_correction)] + '  \n'
        
        text += 'kα1 : {}, kα2 : {}'.format (kalpha1, kalpha2)
        return text

    def downloadParamFile (self,):
        lang = st.session_state['lang']
        with open (self.param_path, 'rb') as f:
            xml_file = f.read()
        
        st.download_button (
                label = {
                    'eng' : 'Down load new parameters',
                    'jpn' : '新しいパラメータのダウンロード'
                    }[lang],
                data = xml_file,
                file_name = 'param.imp.xml'
            )

    def get_result (self, res):
        ans = None
        if res is not None:
            shutil.copyfile (self.out_path_pk, self.out_path)
            ans = read_histo_file (self.out_path)
            hist_name = st.session_state['hist_name']
            st.session_state['peak_name'] = hist_name + '_pk'
        return ans
    
    def reset_files (self,):
        if os.path.exists (self.param_path): os.remove (self.param_path)
        if os.path.exists (self.hist_path): os.remove (self.hist_path)

    def open_param_menu (self, ans):
        #ans = {k : None for k in [
        #    'defaultParam', 'df', 'peakDf', 'nPoints', 'endRegion',
        #    'minRange, maxRange, c_fixed', 'useErr','select',
        #    'kalpha1', 'kalpha2', 'folder', 'log']}
        lang = st.session_state['lang']
        mess_pk = st.session_state['mess_pk']
        with st.expander (
            {'eng' : 'Open parameter menu (Peaksearch)',
             'jpn' : 'パラメータメニュー (ピークサーチ)'}[lang]):
            
            params = st.session_state['params']
            ans['nPoints'], ans['endRegion'] = \
                            self.smthParams (params)
            ans['minRange'], ans['maxRange'] = \
                            self.rangeParam (params)
            ans['c_fixed'],  ans['useErr'] = self.thresholdParam (params)
            select = self.kalpha2Select ()
            ans['select'] = select
        
            if select == mess_pk['exec_sel_1']:
                ans['kalpha1'], ans['kalpha2'] = self.kalpha2Param (params)
        
            self.operationParam (ans, self.param_path)

        return ans
        

    def menu (self,):    
        ans = {k : None for k in [
            'defaultParam', 'df', 'peakDf', 'nPoints', 'endRegion',
            'minRange, maxRange, c_fixed', 'useErr','select',
            'kalpha1', 'kalpha2', 'folder', 'log']}

        if st.session_state['params'] is not None:
            #default_params = st.session_state['default_params']
            #self.display_param (default_params)
            with st.container (border = True):
                ans = self.open_param_menu (ans)
                exec_space = st.empty ()

            with exec_space:
                if os.path.exists (self.param_path) & os.path.exists (self.hist_path):
                    #uploaded_map = self.load_files ()
    
                    res = self.exec_peaksearch ()
                
                    result = self.get_result (res)

                    if result is not None:
                        df, peakDf = result
                        ans['df'] = df; ans['peakDf'] = peakDf
                        st.session_state['df'] = df
                        st.session_state['peakDf'] = peakDf
                        st.session_state['menu_peaksearch'] = True
                        st.session_state['menu_indexing'] = False
                        st.session_state['peakDf_indexing'] = None
                        st.session_state['candidate_exist'] = False

        return ans

if __name__ == '__main__':
    from init import setup_session_state
    setup_session_state ()
    st.session_state['lang'] = 'eng'
    obj = PeakSearchMenu()
    