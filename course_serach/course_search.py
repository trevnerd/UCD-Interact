#%%
from bs4 import BeautifulSoup
import requests
import pandas as pd
import os

#TODO: use a more efficent webscraping technique 
# - this one takes forever and requests so many pages 
# - also I want additional/more informative data
def load_data():
    html = requests.get('https://ucdavis.pubs.curricunet.com/Catalog/courses-subject-code').text
    if not os.path.exists('subject_codes'):
        os.makedirs('subject_codes')
    page = BeautifulSoup(html, 'html.parser')
    subjects = page.find_all('div', {'class': 'col-3'})[0].find_all('li')
    info_list = []
    for i, subject in enumerate(subjects):
        os_file_path = 'subject_codes/' + subject.a['href'].split('/')[-1] + '.html'
        if os.path.isfile(os_file_path):
            with open(os_file_path, 'r', encoding='utf-8') as f:
                courses_html = f.read()
        else:
            courses_html = requests.get('https://ucdavis.pubs.curricunet.com/' + subject.a['href']).text
            with open(os_file_path, 'w', encoding='utf-8') as f:
                f.write(courses_html)
        courses_page = BeautifulSoup(courses_html, 'html.parser')
        courses = courses_page.find_all('div', {'class': 'container-fluid course-summary-wrapper'})

        for course in courses:
            if course.find('span', {'class': 'course-status'})['data-status-alias'] == 'Historical':
                continue
            course_info = {}
            course_info['subject'] = course.find('span', {'class': 'course-subject'}).text
            course_info['number'] = course.find('span', {'class': 'course-number'}).text
            course_info['subject_name'] = courses_page.find('h1').text.split('―')[-1]
            course_info['course_name'] = course.find('span', {'class': 'course-title'}).text
            course_info['credit_amt'] = course.find('span', {'class': 'course-credits'}).text.strip("()")
            course_info['credit_type'] = [ge.text for ge in course.find_all('span', {'class': 'gen-ed-element'})]
            course_summary = course.find('div', {'class': 'col-xs-12 col-sm-12 col-md-12 text-left full-width-column'}).find_all('span', {'title': False})
            
            desc = ''
            prereq_flag = False
            for info in course_summary:
                #print(info)
                if info.text[:9] == 'GE credit':
                    pass
                elif info.text[:12] == 'Prerequisite':
                    prereq_flag = True
                elif prereq_flag:
                    course_info['prerequisites'] = info.text
                    prereq_flag = False
                else:
                    desc = desc.strip() + ' ' + info.text
            if 'prerequisites' not in course_info:
                course_info['prerequisites'] = ''
            course_info['description'] = desc
            #print(course_info)
            info_list.append(course_info)
        print('\r'+str(i+1)+'/'+str(len(subjects)), end='') #progress count
    return info_list

#seperate if statement to prevent reloading data with jupyter notebook when gui testing
if __name__ == '__main__': 
    class_data = load_data()

#%%
if __name__ == '__main__':
    from tkinter import *
    from tkinter import filedialog

    root = Tk()

    #credit
    Label(root, text='Input comma sperated credit values:').grid(row=0, column=0)
    credit_input = Entry(root)
    credit_input.grid(row=0, column=1)

    #GE Subject Areas
    def create_expanding_selectors(label_text, row, types_list, special_null_type='-'):
        Label(root, text=label_text).grid(row=row, column=0)
        selected_vars = [StringVar()] #holds selector variables
        types = [special_null_type] + types_list #ordered list of all options for a selector
        selected_vars[0].set(special_null_type) #default to null character
        selectors = [] #holds selector objects
        def update_selectors(selected_option):
            #append selector new empty selector
            if ((selected_vars[-1].get() != special_null_type and len(selectors) < len(types)-1) or 
               (len(selectors) == len(types)-1 and selected_option == special_null_type)):
                selected_vars.append(StringVar())
                selected_vars[-1].set(special_null_type)
                selectors.append(OptionMenu(root, selected_vars[-1], *types, command=update_selectors))
                selectors[-1].grid(row=row, column=len(selectors))

            i = 0
            selected_types = {var.get() for var in selected_vars if var.get() != special_null_type}
            remaining_types = [typ for typ in types if typ not in selected_types]
            while i < len(selectors):
                selectors[i].grid_forget()
                if selected_vars[i].get() == special_null_type and i != len(selectors)-1: #delete selector
                    selected_vars.pop(i)
                    selectors.pop(i)
                else: #update selector options
                    selectors[i]=OptionMenu(root, selected_vars[i], *remaining_types, command=update_selectors)
                    selectors[i].grid(row=row, column=i+1)
                    i += 1
        
        selectors.append(OptionMenu(root, selected_vars[0], *types, command=update_selectors))
        selectors[0].grid(row=row, column=1)
        return selected_vars

    TB_GEs = create_expanding_selectors('Choose Topical Breadths:', 1, ['AH', 'SE', 'SS'])
    CL_GEs = create_expanding_selectors('Choose Core Literacies:', 2, ['ACGH', 'DD', 'OL', 'QL', 'SL', 'VL', 'WC', 'WE'])
    
    #button
    def export_csv():
        values = {cred.strip() for cred in credit_input.get().split(',')}
        files = [('Excel Files', '*.xlsx')]
        file_location = filedialog.asksaveasfilename(filetypes=files, defaultextension=files)
        str_CL_GEs = [ge.get() for ge in CL_GEs if ge.get() != '-'] #probably should do this better without the if '-'
        str_TB_GEs = [ge.get() for ge in TB_GEs if ge.get() != '-']
        with pd.ExcelWriter(file_location) as writer:
            for str_CL_GE in str_CL_GEs:
                filtered_list = []
                for course in class_data:
                    #this if statement is very dumb lol
                    if course['credit_amt'] in values and any([course_ge in str_TB_GEs for course_ge in course['credit_type']]) and str_CL_GE in course['credit_type']:
                        filtered_list.append(course)
                pd.DataFrame(filtered_list).to_excel(writer, str_CL_GE, index=False)

    credit_button = Button(root, text="Export Classes", command=export_csv)
    credit_button.grid(row=3)

    root.mainloop()
