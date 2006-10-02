# The contents of this file are subject to the Mozilla Public
# License Version 1.1 (the "License"); you may not use this file
# except in compliance with the License. You may obtain a copy of
# the License at http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS
# IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
# implied. See the License for the specific language governing
# rights and limitations under the License.
#
# The Initial Owner of the Original Code is European Environment
# Agency (EEA).  Portions created by Finsiel Romania are
# Copyright (C) European Environment Agency.  All
# Rights Reserved.
#
# Authors:
#
# Alexandru Ghica, Finsiel Romania

#Python imports

#Zope imports
from Globals                                    import InitializeClass
from Products.PageTemplates.PageTemplateFile    import PageTemplateFile
from AccessControl                              import ClassSecurityInfo, getSecurityManager
from AccessControl.Permissions                  import view_management_screens, view

#Product imports
import babelizer
from constants                                      import *
from Products.NaayaBase.constants                   import *
from Products.NaayaContent                          import *
from Products.Naaya.constants                       import *
from Products.NaayaCore.constants                   import *
from Products.NaayaCore.ProfilesTool.ProfileMeta    import ProfileMeta
from Products.Naaya.NySite                          import NySite
from Products.NaayaCore.managers.utils              import utils
from Products.NaayaCore.managers.utils              import file_utils, batch_utils
from Products.NaayaCore.managers.search_tool        import ProxiedTransport
from Products.NaayaCalendar.EventCalendar           import manage_addEventCalendar

manage_addReportSite_html = PageTemplateFile('zpt/site_manage_add', globals())
def manage_addReportSite(self, id='', title='', lang=None, REQUEST=None):
    """ """
    ut = utils()
    id = ut.utCleanupId(id)
    if not id: id = PREFIX_SITE + ut.utGenRandomId(6)
    portal_uid = '%s_%s' % (PREFIX_SITE, ut.utGenerateUID())
    self._setObject(id, ReportSite(id, portal_uid, title, lang))
    self._getOb(id).loadDefaultData()
    if REQUEST is not None:
        return self.manage_main(self, REQUEST, update_menu=1)

class ReportSite(NySite, ProfileMeta):
    """ """

    meta_type = METATYPE_REPORTSITE
    icon = 'misc_/Report/Site.gif'

    manage_options = (
        NySite.manage_options
    )

    security = ClassSecurityInfo()

    def __init__(self, id, portal_uid, title, lang):
        """ """
        NySite.__dict__['__init__'](self, id, portal_uid, title, lang)

    security.declarePrivate('loadDefaultData')
    def loadDefaultData(self):
        """ """
        NySite.__dict__['createPortalTools'](self)
        NySite.__dict__['loadDefaultData'](self)
        #install new objects

        #load site skeleton - configuration
        self.loadSkeleton(join(REPORT_PRODUCT_PATH, 'skel'))

        #load pluggable profiles
        profilestool_ob = self.getProfilesTool()
        profilestool_ob.manageAddProfileMeta('')

        #set default main topics
        try:    self.getPropertiesTool().manageMainTopics(['info', 'reports'])
        except: pass


#####################################################################################
# Utils  #
##########

    def daysLeft(self, REQUEST=None):
        """ """
        today = self.utGetTodayDate()
        finish = self.utGetDate('30/11/2006')
        days_left = int(finish -today)
        if days_left <= 0:
            return 0
        return days_left

    def translate_comment(self, phrase, from_lang='', to_lang='', REQUEST=None):
        """ """
        if not phrase.strip():  return ''
        try:                    return babelizer.translate(phrase, from_lang, to_lang)
        except:                 return ''

    security.declarePublic('getReport')
    def getReport(self):
        """ """
        reports = self.reports.objectValues(METATYPE_NYREPORT)
        if reports:
            return reports[0]
        return []

    #layer over selection lists
    security.declarePublic('getAffiliationList')
    def getAffiliationList(self):
        """
        Return the selection list for affiliations.
        """
        return self.getPortletsTool().getRefListById('affiliation').get_list()

    security.declarePublic('searchAffiliationList')
    def searchAffiliationList(self, affiliation):
        """ search in the affiliations list"""
        return [aff for aff in self.getAffiliationList() if aff.id == affiliation]

    security.declarePublic('getAffiliationById')
    def getAffiliationById(self, id):
        """ return affiliation by id """
        for aff in self.getAffiliationList():
            if aff.id == id:
                return aff.title

#####################################################################################
# Cross-references #
####################

    security.declarePublic('getReferenceData')
    def getReferenceData(self, str):
        """ """
        try:
            search_string = u'"%s"' % str
            return [k.absolute_url(1) for k in self.getCatalogedObjects(meta_type=[METATYPE_NYREPORTCHAPTER, METATYPE_NYREPORTSECTION], objectkeywords_en=search_string)]
        except:
            return []

    security.declareProtected(PERMISSION_EDIT_OBJECTS, 'indexCrossReferences')
    def indexCrossReferences(self):
        """ """
        for ref_ob in self.getReport().getCrossReferences():
            ref_links = {}
            ref_links['en'] = self.getReferenceData(ref_ob.getLocalProperty('reference', 'en'))
            ref_ob.ref_links = ref_links
            ref_ob._p_changed = 1

    security.declareProtected(PERMISSION_EDIT_OBJECTS, 'indexCrossReferences')
    def getTitleByURL(self, p_url):
        """ """
        try:    return self.unrestrictedTraverse(p_url, None)
        except: return None

    security.declareProtected(view, 'admin_references_html')
    def admin_references_html(self, REQUEST=None, RESPONSE=None):
        """ """
        return self.getFormsTool().getContent({'here': self}, 'site_admin_references')

#####################################################################################
# Profiles #
############

    def update_profiles(self):
        """ """
        #load pluggable profiles
        profilestool_ob = self.getProfilesTool()
        profilestool_ob.manageAddProfileMeta('')

    security.declarePrivate('loadProfileMeta')
    def loadProfileMeta(self):
        """
        Load profile metadata and updates existing profiles.
        """
        self._loadProfileMeta(join(REPORT_PRODUCT_PATH, 'skel', 'others'))

    security.declareProtected(view, 'profilesheet')
    def profilesheet(self, name=None, affiliation='', nationality='', REQUEST=None):
        """
        Updates the profile of the given user. Must be implemented.
        """
        if name is None: name = self.REQUEST.AUTHENTICATED_USER.getUserName()
        self._profilesheet(name, {'affiliation': affiliation, 'nationality':nationality})
        if REQUEST:
            self.setSessionInfo([MESSAGE_SAVEDCHANGES % self.utGetTodayDate()])
            REQUEST.RESPONSE.redirect('%s/profilesheet_html' % self.absolute_url())

    security.declareProtected(view, 'profilesheet_html')
    def profilesheet_html(self, REQUEST=None, RESPONSE=None):
        """
        View for instance associated sheet. Must be implemented.
        """
        return self.getFormsTool().getContent({'here': self}, 'site_profilesheet')

#####################################################################################
# Request role #
################

    def setRequestRoleSession(self, name, firstname, lastname, email, password,
        nationality, affiliation):
        """ """
        self.setUserSession(name, '', '', firstname, lastname, email, password)
        self.setSession('user_nationality', nationality)
        self.setSession('user_affiliation', affiliation)

    def delRequestRoleSession(self):
        """ """
        self.delUserSession()
        self.delSession('user_nationality')
        self.delSession('user_affiliation')

    def getSessionUserNationality(self, default=''):
        return self.getSession('user_nationality', default)

    def getSessionUserAffiliation(self, default=''):
        return self.getSession('user_affiliation', default)

    security.declareProtected(view, 'processRequestRoleForm')
    def processRequestRoleForm(self, username='', password='', confirm='', firstname='', lastname='', email='', nationality='', affiliation='', affiliation_other='', REQUEST=None):
        """ """
        affiliation_title = self.getAffiliationById(affiliation)
        if affiliation_other:
            affiliation = affiliation_title = affiliation_other
        #create an account without role
        try:
            self.getAuthenticationTool().manage_addUser(username, password, confirm, [], [], firstname,
                lastname, email)
            profile = self.getProfilesTool().getProfile(username)
            sheet = profile.getSheetById(self.getInstanceSheetId())
            sheet.nationality = nationality
            sheet.affiliation = affiliation
        except Exception, error:
            err = error
        else:
            err = ''
        if err:
            if REQUEST:
                self.setSessionErrors(err)
                self.setRequestRoleSession(username, firstname, lastname, email, password, nationality, affiliation)
                return REQUEST.RESPONSE.redirect(REQUEST.HTTP_REFERER)
        if not err:
            self.sendRequestRoleEmail(self.administrator_email, username, '%s %s' % (firstname, lastname), email, nationality, affiliation_title)
        if REQUEST:
            self.setSession('title', 'Thank you for registering')
            self.setSession('body', 'An account has been created for you. \
                The administrator will be informed of your request and may \
                or may not grant your account with the approriate role.')
            REQUEST.RESPONSE.redirect('%s/messages_html' % self.absolute_url())

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'admin_addroles')
    def admin_addroles(self, names=[], roles=[], loc='allsite', location='', REQUEST=None):
        """ """
        msg = err = ''
        names = self.utConvertToList(names)
        if len(names)<=0:
            err = 'An username must be specified'
        else:
            err = None
            try:
                for name in names:
                    self.getAuthenticationTool().manage_addUsersRoles(name, roles, loc, location)
            except Exception, error:
                err = error
            else:
                msg = MESSAGE_SAVEDCHANGES % self.utGetTodayDate()
            if not err:
                auth_tool = self.getAuthenticationTool()
                for name in names:
                    user_ob = auth_tool.getUser(name)
                    self.sendCreateAccountEmail('%s %s' % (user_ob.firstname, user_ob.lastname), user_ob.email, user_ob.name, REQUEST)
        if REQUEST:
            if err: self.setSessionErrors([err])
            if msg: self.setSessionInfo([msg])
            REQUEST.RESPONSE.redirect('%s/admin_roles_html' % self.absolute_url())

#####################################################################################
# Email templates #
###################

    def sendCreateAccountEmail(self, p_name, p_email, p_username, REQUEST):
        #sends a confirmation email to the newlly created account's owner
        email_template = self.getEmailTool()._getOb('email_createaccount')
        l_subject = email_template.title
        l_content = email_template.body
        l_content = l_content.replace('@@PORTAL_URL@@', self.portal_url)
        l_content = l_content.replace('@@PORTAL_TITLE@@', self.site_title)
        l_content = l_content.replace('@@NAME@@', p_name)
        l_content = l_content.replace('@@USERNAME@@', p_username)
        #l_content = l_content.replace('@@TIMEOFPOST@@', str(self.utGetTodayDate()))
        mail_from = self.mail_address_from
        self.getEmailTool().sendEmail(l_content, p_email, mail_from, l_subject)

    def sendRequestRoleEmail(self, p_to, p_username, p_name, p_email, p_nationality, p_affiliation):
        #sends a request role email
        email_template = self.getEmailTool()._getOb('email_requestrole')
        l_subject = email_template.title
        l_content = email_template.body
        l_content = l_content.replace('@@NAME@@', p_name)
        l_content = l_content.replace('@@EMAIL@@', p_email)
        l_content = l_content.replace('@@NATIONALITY@@', p_nationality)
        l_content = l_content.replace('@@AFFILIATION@@', p_affiliation)
        l_content = l_content.replace('@@USERNAME@@', p_username)
        l_content = l_content.replace('@@PORTAL_URL@@', self.portal_url)
        l_content = l_content.replace('@@PORTAL_TITLE@@', self.site_title)
        l_content = l_content.replace('@@TIMEOFPOST@@', str(self.utGetTodayDate()))
        self.getEmailTool().sendEmail(l_content, p_to, p_email, l_subject)

#####################################################################################
# Site map generation #
#######################

    # Generic sitemap functions
    def getSiteMap(self, expand=[], root=None, showitems=0):
        #returns a list of objects with additional information
        #in order to draw the site map
        if root is None: root = self
        return self.__getSiteMap(root, showitems, expand, 0)

    def getSiteMapTrail(self, expand, tree):
        #given a list with all tree nodes, returns a string with all relatives urls
        if expand == 'all': return ','.join([node[0].absolute_url(1) for node in tree])
        else: return expand

    def __getSiteMap(self, root, showitems, expand, depth):
        #site map core
        l_tree = []
        l_folders = [x for x in root.objectValues(self.get_belgrade_containers_metatypes()) if x.approved == 1 and x.submitted==1]
        l_folders = self.utSortObjsListByAttr(l_folders, 'sortorder', 0)
        for l_folder in l_folders:
            if len(l_folder.objectValues(self.get_belgrade_containers_metatypes())) > 0 or (len(l_folder.getObjects()) > 0 and showitems==1):
                if l_folder.absolute_url(1) in expand or 'all' in expand:
                    l_tree.append((l_folder, 0, depth))
                    if showitems:
                        buf = [x for x in l_folder.getPublishedObjects()]
                        for l_item in buf:
                            l_tree.append((l_item, -1, depth+1))
                    l_tree.extend(self.__getSiteMap(l_folder, showitems, expand, depth+1))
                else:
                    l_tree.append((l_folder, 1, depth))
            else:
                l_tree.append((l_folder, -1, depth))
        return l_tree

    # Remotechannels-specific sitemap functions
    def getSiteMapRemCh(self, expand=[], root=None, showitems=0):
        #returns a list of objects with additional information
        #in order to draw the site map
        if root is None: root = self
        return self.__getSiteMapRemCh(root, showitems, expand, 0)

    def __getSiteMapRemCh(self, root, showitems, expand, depth):
        #site map for Remotechannels
        l_tree = []
        l_folders = [x for x in root.objectValues(self.get_belgrade_containers_metatypes()) if x.approved == 1 and x.submitted==1]
        l_folders = self.utSortObjsListByAttr(l_folders, 'sortorder', 0)
        for l_folder in l_folders:
            if len(l_folder.objectValues(self.get_belgrade_containers_metatypes())) > 0 or (len(l_folder.getObjects()) > 0 and showitems==1):
                if l_folder.absolute_url(1) in expand or 'all' in expand:
                    l_tree.append((l_folder, 0, depth))
                    if showitems:
                        buf = [x for x in l_folder.getPublishedObjects()]
                        for l_item in buf:
                            l_tree.append((l_item, -1, depth+1))
                    l_tree.extend(self.__getSiteMap(l_folder, showitems, expand, depth+1))
                else:
                    l_tree.append((l_folder, 1, depth))
            else:
                l_tree.append((l_folder, -1, depth))
        return l_tree

    # Belgrade-specific sitemap functions
    def get_belgrade_containers_metatypes(self):
        #Belgrade specific meta_types
        return [METATYPE_FOLDER, METATYPE_NYREPORTCHAPTER, METATYPE_NYREPORTSECTION, METATYPE_NYREPORT]

    def getSiteMapBelgrade(self, expand=[], root=None, showitems=0):
        #returns a list of objects with additional information
        #in order to draw the site map
        print root
        if root is None: root = self
        return self.__getSiteMapBelgrade(root, showitems, expand, 0, 4)

    def _get_non_folderish_objects(self, container):
        return [ obj for obj in container.objectValues() if obj.meta_type not in self.get_containers_metatypes() ]

    def __getSiteMapBelgrade(self, root, showitems, expand, depth, maxdepth):
        #custom function for the Belgrade websites
        #has specific expanded nodes
        l_maintopics = self.getMainTopics()
        l_tree = []
        if root is self:
            l_folders = [x for x in root.objectValues(self.get_belgrade_containers_metatypes()) if x.approved == 1 and x.submitted==1 and x in l_maintopics]
        else: 
            l_folders = root.getPublishedFolders()
            l_folders.extend(root.objectValues(METATYPE_NYREPORTCHAPTER))
            l_folders.extend(root.objectValues(METATYPE_NYREPORTSECTION))
            l_folders.extend(root.objectValues(METATYPE_NYREPORT))
        l_folders = self.utSortObjsListByAttr(l_folders, 'sortorder', 0)
        for l_folder in l_folders:
            if ((len(l_folder.objectValues(self.get_belgrade_containers_metatypes())) > 0) or ((len(l_folder.getObjects()) > 0) and showitems==1) or (l_folder.id=='about' and self is root)):
                if l_folder.absolute_url(1) in expand or 'all' in expand:
                    l_tree.append((l_folder, 0, depth))
                    if showitems:
                        for l_item in l_folder.getPublishedObjects():
                            l_tree.append((l_item, -1, depth+1))
                    l_tree.extend(self.__getSiteMapBelgrade(l_folder, showitems, expand, depth+1, maxdepth))
                else:
                    l_tree.append((l_folder, 1, depth))
            else:
                l_tree.append((l_folder, -1, depth))
            if ((root is self) and (l_folder.id=='about') and (l_folder.absolute_url(1) in expand or 'all' in expand)):
                for element in self.utSortObjsListByAttr(self._get_non_folderish_objects(l_folder),'sortorder',0):
                    l_tree.append((element, -1, 1))
        return l_tree

#####################################################################################
# Update scripts #
##################

    security.declarePublic('update_images_path')
    def update_images_path(self):
        """ update images path according to the new Epoz update """
        catalog = self.getCatalogTool()

        for sec in catalog.query_objects_ex(meta_type=['Naaya Report Section']):
            for img in sec.objectValues('Image'):
                #image path
                old_path = img.absolute_url(1).replace("/cap", "/rep").replace("/sec", "/rep")
                old_path = old_path.replace("belgrade3", "http://belgrade1.finsiel.ro")
                #new_path = img.absolute_url(1)
                new_path = img.getId()

                #description
                old_descr = sec.getLocalProperty('description', 'en')
                new_descr = old_descr.replace(old_path, new_path)

                #test bad values
                if old_descr.find('src="http://') != -1:
                    #print sec.absolute_url()
                    pass

                #update objects
                sec.save_properties(sec.getLocalProperty('title', 'en'), new_descr, sec.getLocalProperty('coverage', 'en'), 
                    sec.getLocalProperty('keywords', 'en'), sec.sortorder, sec.releasedate, 'en')
                sec._p_changed = 1

        return True

InitializeClass(ReportSite)
