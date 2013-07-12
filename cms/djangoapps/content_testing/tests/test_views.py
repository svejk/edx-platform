from contentstore.tests.test_course_settings import CourseTestCase
from xmodule.modulestore.tests.factories import ItemFactory
from capa.tests.response_xml_factory import CustomResponseXMLFactory
from content_testing.models import ContentTest
from textwrap import dedent

class TestProblemViewTest (CourseTestCase):
    """
    Tests for the views involved in the automated content testing
    """

    SCRIPT = dedent("""
    def is_prime (n):
        primality = True
        for i in range(2,int(math.sqrt(n))+1):
            if n%i == 0:
                primality = False
                break
        return primality

    def test_prime(expect,ans):
        a1=int(ans)
        return is_prime(a1)""").strip()

    def setUp(self):
        """
        override parent setUp to put a problem in that course
        """

        super(TestProblemViewTest, self).setUp()

        #make the problem
        custom_template = "i4x://edx/templates/problem/Custom_Python-Evaluated_Input"

        #change the script if 1
        problem_xml = CustomResponseXMLFactory().build_xml(
            script=self.SCRIPT,
            cfn='test_prime')

        self.problem = ItemFactory.create(
            parent_location=self.course_location,
            data=problem_xml,
            template=custom_template)

        # format as if it came from the form generated by the capa_problem
        #sigh
        self.input_id_base = self.problem.id.replace('://', '-').replace('/', '-')


    def create_model(self):
        """
        helper method to add a content test to the database and return the pk
        """

        # saved responses for making tests
        self.response_dict_correct = {
            self.input_id_base + '_2_1': '5'
        }

        self.response_dict_incorrect = {
            self.input_id_base + '_2_1': '6'
        }

        pass_correct = ContentTest.objects.create(
            problem_location=self.problem.location,
            should_be='Correct',
            response_dict=self.response_dict_correct
        )

        return pass_correct.pk


    def check_no_models(self, response):
        """
        check that there are no tests in this summary
        """

        assert not("id_to_edit" in response.content)
        assert ("create_new_button" in response.content)
        self.assertEqual(ContentTest.objects.all().count(), 0)

    def check_exist_models(self, response):
        """
        check that there are tests in the summary view
        """

        assert ("id_to_edit" in response.content)
        assert("Run Tests" in response.content)
        assert ("create_new_button" in response.content)
        self.assertGreater(ContentTest.objects.all().count(), 0)

    def test_no_tests(self):
        """
        test that initially there are no tests for the problem
        """

        url = "/test_problem/?location="+str(self.problem.location)
        response = self.client.get(url)
        self.check_no_models(response)

    def test_create_test(self):
        """
        test that the create new displays properly
        """

        url = "/test_problem/new/"
        get_data = {'location': str(self.problem.location)}
        response = self.client.get(url, get_data)

        assert ("save" in response.content)

    def test_save_new(self):
        """
        test that saving a new test works
        """

        # format the response that the capa problem generates
        input_id = 'input_'+self.input_id_base+'_2_1'
        post_data = {
            'location': str(self.problem.location),
            'should_be': 'Correct',
            input_id: '5'
        }

        url = "/test_problem/save/?location="+str(self.problem.location)
        response = self.client.post(url, post_data, follow=True)

        # chack that we were redirected to the right place and that the test now shows up
        self.assertRedirects(response, '/test_problem/?location='+str(self.problem.location))
        self.check_exist_models(response)

    def test_save_edit(self):
        """
        test that editing existing works
        """

        model_id = self.create_model()

        # create save request with problem ID to edit
        input_id = 'input_'+self.input_id_base+'_2_1'
        post_data = {
            'location': str(self.problem.location),
            'should_be': 'Incorrect',
            input_id: '4',
            'id_to_edit': model_id
        }

        url = "/test_problem/save/?location="+str(self.problem.location)
        response = self.client.post(url, post_data, follow=True)

        # chack that we were redirected to the right place and that the test now shows up
        self.assertRedirects(response, '/test_problem/?location='+str(self.problem.location))
        self.check_exist_models(response)

        # check that the test was in fact edited
        model = ContentTest.objects.get(pk=model_id)
        self.assertEqual(model.should_be, 'Incorrect')