def create_data_list(projects):


    ## Titles
    values = [['Name',
               'Viewed', 'Views as % Total',
               'Engaged','Enagaged as % Views',
               'Complete', 'Complete as % Views',
               'Final','Print',
               'Curriculum Level', 'Design', 'Programming', 'Phys-comp', 'Manufacture', 'Community',
               'duration',
               'learning_hours']]

    ## Find total project views
    total_views = 0
    for project in projects.keys():
        try:
            total_views += int(projects[project]['analytics']['1'][1])
        except KeyError:
            print('No analytics available for', project, 'for this month')

    ## Assemble values for spreadsheet

    
    for project in projects.keys():
        try:
            viewed_first_page = int(projects[project]['analytics']['1'][1])
            try:
                views_as_percentage = viewed_first_page / total_views * 100
            except ZeroDivisionError:
                views_as_percentage = 0
            engaged = int(projects[project]['analytics']['3'][1])
            try:
                engaged_as_percentage = engaged / viewed_first_page * 100
            except ZeroDivisionError:
                engaged_as_percentage = 0
            ## Find last page
            pages = []
            for page in projects[project]['analytics'].keys():
                try:
                    pages.append(int(page))
                except ValueError:
                    pass
            final = str(max(pages))

            complete = int(projects[project]['analytics'][final][1])
            try:
                complete_as_percentage = complete / viewed_first_page * 100
            except ZeroDivisionError:
                complete_as_percentage = 0
            try:
                final = int(projects[project]['analytics']['complete'][1])
            except KeyError:
                final = 0

            try:
                printed = int(projects[project]['analytics']['print'][1])
            except KeyError:
                printed = 0
                
            curriculum = refine_curriculum(projects[project]['curriculum'])
            level = int(curriculum['level'])
            design =int(curriculum['design'])
            programming = int(curriculum['programming'])
            phys = int(curriculum['phys'])
            manufacture = int(curriculum['manufacture'])
            community =  int(curriculum['community'])

            duration = int(projects[project]['duration'])
            if duration == 1:
                learning_hours = 0.25 * complete
            elif duration == 2:
                learning_hours = 1 * complete
            elif duration == 3:
                learning_hours = 2 * complete
            else:
                learning_hours = 0

            values.append([project,
                           viewed_first_page,
                           views_as_percentage,
                           engaged,
                           engaged_as_percentage,
                           complete,
                           complete_as_percentage,
                           final,
                           printed,
                           level,
                           design,
                           programming,
                           phys,
                           manufacture,
                           community,
                           duration,
                           learning_hours])
        except KeyError:
            print(project)
    return values
