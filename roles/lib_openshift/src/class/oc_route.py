# pylint: skip-file
# flake8: noqa


# pylint: disable=too-many-instance-attributes
class OCRoute(OpenShiftCLI):
    ''' Class to wrap the oc command line tools '''
    kind = 'route'

    def __init__(self,
                 config,
                 verbose=False):
        ''' Constructor for OCVolume '''
        super(OCRoute, self).__init__(config.namespace, config.kubeconfig)
        self.config = config
        self.namespace = config.namespace
        self._route = None

    @property
    def route(self):
        ''' property function for route'''
        if not self._route:
            self.get()
        return self._route

    @route.setter
    def route(self, data):
        ''' setter function for route '''
        self._route = data

    def exists(self):
        ''' return whether a route exists '''
        if self.route:
            return True

        return False

    def get(self):
        '''return route information '''
        result = self._get(self.kind, self.config.name)
        if result['returncode'] == 0:
            self.route = Route(content=result['results'][0])
        elif 'routes \"%s\" not found' % self.config.name in result['stderr']:
            result['returncode'] = 0
            result['results'] = [{}]

        return result

    def delete(self):
        '''delete the object'''
        return self._delete(self.kind, self.config.name)

    def create(self):
        '''create the object'''
        return self._create_from_content(self.config.name, self.config.data)

    def update(self):
        '''update the object'''
        # need to update the tls information and the service name
        return self._replace_content(self.kind, self.config.name, self.config.data)

    def needs_update(self):
        ''' verify an update is needed '''
        skip = []
        return not Utils.check_def_equal(self.config.data, self.route.yaml_dict, skip_keys=skip, debug=True)

    # pylint: disable=too-many-return-statements,too-many-branches
    @staticmethod
    def run_ansible(params, files, check_mode=False):
        ''' run the idempotent asnible code

            params comes from the ansible portion for this module
            files: a dictionary for the certificates
                   {'cert': {'path': '',
                             'content': '',
                             'value': ''
                            }
                   }
            check_mode: does the module support check mode.  (module.check_mode)
        '''

        rconfig = RouteConfig(params['name'],
                              params['namespace'],
                              params['kubeconfig'],
                              files['destcacert']['value'],
                              files['cacert']['value'],
                              files['cert']['value'],
                              files['key']['value'],
                              params['host'],
                              params['tls_termination'],
                              params['service_name'])

        oc_route = OCRoute(rconfig, verbose=params['debug'])

        state = params['state']

        api_rval = oc_route.get()

        #####
        # Get
        #####
        if state == 'list':
            return {'changed': False,
                    'results': api_rval['results'],
                    'state': 'list'}

        ########
        # Delete
        ########
        if state == 'absent':
            if oc_route.exists():

                if check_mode:
                    return {'changed': False, 'msg': 'CHECK_MODE: Would have performed a delete.'}  # noqa: E501

                api_rval = oc_route.delete()

                return {'changed': True, 'results': api_rval, 'state': "absent"}  # noqa: E501
            return {'changed': False, 'state': 'absent'}

        if state == 'present':
            ########
            # Create
            ########
            if not oc_route.exists():

                if check_mode:
                    return {'changed': True, 'msg': 'CHECK_MODE: Would have performed a create.'}  # noqa: E501

                # Create it here
                api_rval = oc_route.create()

                if api_rval['returncode'] != 0:
                    return {'failed': True, 'results': api_rval, 'state': "present"}  # noqa: E501

                # return the created object
                api_rval = oc_route.get()

                if api_rval['returncode'] != 0:
                    return {'failed': True, 'results': api_rval, 'state': "present"}  # noqa: E501

                return {'changed': True, 'results': api_rval, 'state': "present"}  # noqa: E501

            ########
            # Update
            ########
            if oc_route.needs_update():

                if check_mode:
                    return {'changed': True, 'msg': 'CHECK_MODE: Would have performed an update.'}  # noqa: E501

                api_rval = oc_route.update()

                if api_rval['returncode'] != 0:
                    return {'failed': True, 'results': api_rval, 'state': "present"}  # noqa: E501

                # return the created object
                api_rval = oc_route.get()

                if api_rval['returncode'] != 0:
                    return {'failed': True, 'results': api_rval, 'state': "present"}  # noqa: E501

                return {'changed': True, 'results': api_rval, 'state': "present"}  # noqa: E501

            return {'changed': False, 'results': api_rval, 'state': "present"}

        # catch all
        return {'failed': True, 'msg': "Unknown State passed"}