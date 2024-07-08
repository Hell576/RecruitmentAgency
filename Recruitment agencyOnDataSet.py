#import sys
import PySimpleGUI as sg
import dataset
import gzip
import delegator


# =============================================================================
# def running_windows():
#     return sys.platform.startswith('win')
# 
# =============================================================================

def clear_odd_sym(str):
    new_str = ''
    for i in str:
        if (i == ' ' 
            or ord(i) in range(ord('0'), ord('9')) #or str.isalnum()
            or ord(i) in range(ord('A'), ord('Z'))
            or ord(i) in range(ord('a'), ord('z')) 
            or ord(i) in range(ord('А'), ord('Я'))
            or ord(i) in range(ord('а'), ord('я'))):
                new_str = new_str + i
    return new_str

def show_STRvacancies(database, list_keys, where_SQLclause=''):
    list_keys.clear()
    str_vacancies = []
    query = database.query('SELECT uk_vacancy, position, vacancy.uk_company FROM vacancy '
                           + where_SQLclause + ' ORDER BY vacancy.position ASC')
    counter = 0
    for row in query:
        find_out_company = database['company'].find_one(uk_company={'=':row['uk_company']})
        str_vacancies.append(row['position'] + find_out_company['company_name'])
        #str_vacancies[-1] = clear_odd_sym(str_vacancies[-1])
        list_keys[counter] = row['uk_vacancy']
        counter += 1

    return str_vacancies

def recovery_if_need(database):
    recovery_date = database.get_table('recovery')
    if (len(database['recovery'].columns) == 0):
        # id with primary key creates and fills automatically
          # recovery_date.create_column('key', database.types.integer, primary_key=True, nullable=False, start=1, increment=1)
           recovery_date.create_column('last_recovery', database.types.datetime, nullable=False) 
        
    time_to = database.query("""
                   WITH diff AS
                    (SELECT NOW() -
                    (SELECT last_recovery
                    FROM recovery
                    ORDER BY id DESC
                    LIMIT 1) AS d)
                    
                    SELECT 
                    CASE d >= interval '1 day'
                    WHEN true THEN 'TRUE' ELSE 'FALSE'
                    END
                    FROM diff;
                   """)
    is_time = False
    for i in time_to:
        is_time = i['case']
        
    print(len(database['recovery']) == 0 or is_time)
    if ((len(database['recovery']) == 0 or is_time) == True): #len(database['recovery']) is amount of rows in table
            print('begin')
            database.begin()
            database.query('INSERT INTO recovery(last_recovery) SELECT NOW()')
            #execute subprocess
            with gzip.open('kadr_agency_bkp.gz', 'wb') as f:
                c = delegator.run('pg_dump -h localhost -U postgres -W -Max777- kadr_agency')
                f.write(c.out.encode('utf-8'))
            #end execution
            database.commit()
            print('commited')    
    
def make_window(database):

    theme = sg.OFFICIAL_PYSIMPLEGUI_THEME
    sg.theme(theme)

    list_keys = {}
    left_col = sg.Column([
        [sg.Listbox(values=show_STRvacancies(database, list_keys), select_mode=sg.SELECT_MODE_SINGLE,
         size=(50,20), enable_events=True, bind_return_key=True, key='-VACANCY LIST-', metadata=list_keys) ],
        [sg.Text('Поиск вакансий:'), sg.Input(size=(25, 1),
         focus=True, enable_events=True, key='-FILTER-'),
         sg.T(size=(15,1), k='-FILTER NUMBER-')],
        ], element_justification='l', expand_x=True, expand_y=True)

    
    right_col = [
        [sg.Multiline(size=(70, 21), key='-MORE INFO-', reroute_stdout=True, echo_stdout_stderr=True, reroute_cprint=True)],
        [sg.Button(button_text='Подать заявку', disabled=True, enable_events=True, key='-SUBMIT-')]
    ]

    

    layout = [[sg.Text('Выберите вакансию', font='Any 20')],
              [sg.Pane([sg.Column([[left_col]], element_justification='l',  expand_x=True, expand_y=True), 
                        sg.Column(right_col, element_justification='c', expand_x=True, expand_y=True) ], orientation='h', relief=sg.RELIEF_SUNKEN, k='-PANE-')],
             ]

    window = sg.Window('Recruitment Agency', layout, finalize=True, icon=icon, resizable=True, use_default_focus=False)
    window.set_min_size(window.size)

    window['-VACANCY LIST-'].expand(True, True, True)
    window['-PANE-'].expand(True, True, True)

    # sg.cprint_set_output_destination(window, ML_KEY)
    return window, list_keys

def choose_mode_window():
    keys = ['Соискатель', 'Менеджер', 'Предприятие']
    layout = [
        [sg.T('КТО?!', font='DEFAULT 25')],
        [sg.Button(name) for name in keys ]
        ] 
    window = sg.Window('Choose mode', layout)
    
    while True:
        event, values = window.read()
        if event in (sg.WINDOW_CLOSED, 'Exit'):
            break
        if event == keys[0]:
            window.close()
            return keys[0]
            break
        elif event == keys[1]:
            window.close()
            return keys[1]
            break
        elif event == keys[2]:
            window.close()
            return keys[2]
            break
            
def input_id_window():
    return sg.popup_get_text('Ввод ID', 'Введите свой ID')
            
def main_window(db, app_id):
    window, list_keys = make_window(db)
    vacc_query = []   
    while True:
            event, values = window.read()
            if event in (sg.WINDOW_CLOSED, 'Exit'):
                break
            
            window['-SUBMIT-'].update(disabled=True)
            if event == '-VACANCY LIST-':     
                chosen = window['-VACANCY LIST-'].get_indexes()#.Widget.curselection()
                if (len(chosen) != 0):
                    query = db['vacancy'].find_one(uk_vacancy={'=':list_keys[chosen[0]]}) 
                    
                    find_out_company = db['company'].find_one(uk_company={'=':query['uk_company']})
                    
                    format = "\n".join([f'Компания: {find_out_company["company_name"]}',
                                        f'Должность: {query["position"]}',
                                        '-------------',
                                        'Требования',
                                        '-------------',
                                        f'Гражданство: {query["citizenship"]}',
                                        f'Образование: {query["education"]}',
                                        f'Опыт работы(годы, лет): {query["job_exper"]}',
                                        f'Заработная плата: {query["min_wage"]} руб']
                                        )
                                                
                    window['-MORE INFO-'].update(format)
                    vacc_query = query
                    window['-SUBMIT-'].update(disabled=False)
             
            if event == '-SUBMIT-':
                        #print(vacc_query)
                        for res in db.query("""SELECT COUNT(*) count 
                                            FROM requests WHERE uk_applicant = """ + str(app_id) + ' AND uk_vacancy = ' 
                                            + str(vacc_query['uk_vacancy']) + ' LIMIT 1'):
                            if (res['count'] == 0): 
                                 db.query(f"""
                                          INSERT INTO requests(uk_vacancy, uk_applicant)
                                          VALUES({vacc_query['uk_vacancy']}, {app_id})""")
                                 sg.popup('Заявка подана')
                            else: sg.popup_error('Заявка уже подана')
            elif event == '-FILTER-':
                window['-MORE INFO-'].update('')
                new_vacc_list = show_STRvacancies(db, list_keys, f'WHERE  position ILIKE \'%{values["-FILTER-"]}%\'')
                window['-VACANCY LIST-'].update(new_vacc_list)
                
                if (len(new_vacc_list) == 1): window['-FILTER NUMBER-'].update(f'{len(new_vacc_list)} вакансия')
                elif (len(new_vacc_list) > 4): window['-FILTER NUMBER-'].update(f'{len(new_vacc_list)} вакансий')
                else: window['-FILTER NUMBER-'].update(f'{len(new_vacc_list)} вакансии')
            
    window.close()
        
def main():
    if (choose_mode_window() == 'Соискатель'):
        db = dataset.connect('postgresql://postgres:-Max777-@localhost/kadr_agency')
        #recovery_if_need(db)       
        #db.freeze(db['company'].all(), format='json', filename='reccopy.json')
        used = False
        while used != True:
            app_id = str(input_id_window())
            if (app_id.isdigit() == True):
                for res in db.query('SELECT COUNT(*) count FROM applicant WHERE uk_applicant = ' + app_id + ' LIMIT 1'):
                    if (res['count'] > 0): 
                        
                        main_window(db, app_id)
                        print("Here I am")
                        used = True
                    else: print('Такого ID нет')
                
            else: print('ВЫ ХОТЬ ПОНИМАЕТЕ ЧТО ВЫ ВВЕЛИ??')
        
        
        
        
    

if __name__ == '__main__':
    icon = 'icon.jpg'
    try:
        version = sg.version
        version_parts = version.split('.')
        major_version, minor_version = int(version_parts[0]), int(version_parts[1])
        if major_version < 4 or minor_version < 32:
            sg.popup('Warning - Your PySimpleGUI version is less then 4.35.0',
                     'As a result, you will not be able to use the EDIT features of this program',
                     'Please upgrade to at least 4.35.0',
                     f'You are currently running version:',
                     sg.version,
                     background_color='red', text_color='white')
    except Exception as e:
        print(f'** Warning Exception parsing version: {version} **  ', f'{e}')
    main()