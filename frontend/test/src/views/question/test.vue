<template>
  <div class="m-question-test" v-loading.body="loading">
    <el-form ref="form" :model="answer" label-width="100px">
      <el-form-item label="题目详情" prop="desc">{{form.desc}}</el-form-item>
      <el-form-item
        label="难易度"
        prop="difficulty"
      >{{utils.generateTitle(form.difficulty, 'question.difficulty')}}</el-form-item>
      <el-form-item label="题目类型" prop="type">{{utils.generateTitle(form.type, 'question.type')}}</el-form-item>
      <el-form-item label="题目">
        <el-table :data="form.question" style="width: 100%" border stripe>
          <el-table-column type="index" width="50"></el-table-column>
          <el-table-column label="问题" width="250">
            <template slot-scope="scope">
              <el-input
                v-if="CONTENT_TYPE['TEXT'] === scope.row['type']"
                v-model="scope.row.content"
                autosize
              ></el-input>
              <img v-else :src="$store.getters.backendUrl + scope.row.content" autosize />
            </template>
          </el-table-column>
          <el-table-column label="答案">
            <template slot-scope="{row}">
              <el-form-item
                :prop="String(row['num'])"
                v-bind:key="row['num']"
                :rules="[
                 QUESTION_TYPE['CHECKBOX']===form['type']?
                 { type:'array', required: true, message: '请完善答案', trigger: 'change' }:
                 { required: true, message: '请完善答案', trigger: 'change' }
              ],"
              >
                <!-- 选择题：单选 -->
                <el-radio-group
                  v-if="QUESTION_TYPE['RADIO']===form['type']"
                  v-model="answer[row['num']]"
                >
                  <el-radio-button
                    v-for="(item,index) in getCandidate(row)"
                    :key="index"
                    :label="item.num"
                  >
                    <!-- 选项类型：图片/文字 -->
                    <template v-if="CONTENT_TYPE['TEXT']===item.type">{{item.content}}</template>
                    <img v-else :src="$store.getters.backendUrl + item.content" autosize />
                  </el-radio-button>
                </el-radio-group>
                <!-- 选择题：多选 -->
                <el-checkbox-group
                  v-else-if="QUESTION_TYPE['CHECKBOX']===form['type']"
                  v-model="answer[row['num']]"
                >
                  <el-checkbox
                    v-for="(item,index) in getCandidate(row)"
                    :key="index"
                    :label="item.num"
                  >
                    <!-- 选项类型：图片/文字 -->
                    <template v-if="CONTENT_TYPE['TEXT']===item.type">{{item.content}}</template>
                    <img v-else :src="$store.getters.backendUrl + item.content" autosize />
                  </el-checkbox>
                </el-checkbox-group>
                <!-- 填空题 -->
                <el-input
                  v-else-if="QUESTION_TYPE['INPUT']===form['type']"
                  v-model.trim="answer[row['num']]"
                ></el-input>
              </el-form-item>
            </template>
          </el-table-column>
        </el-table>
      </el-form-item>
      <el-form-item v-if="!queryId">
        <el-button
          @click="submitForm"
          type="primary"
          class="wrap-width"
          v-loading="loading"
        >{{$t('submit')}}</el-button>
        <br />
        <el-button @click="testUser" type="primary" class="wrap-width" v-loading="loading">查看当前用户</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script>
import { getUser } from '@/api/user'
import { nextQuestion, showQuestion, firstQuestion } from '@/api/question'
import { QUESTION_TYPE, QUESTION_LEVEL, CONTENT_TYPE, CANDIDATE_TYPE } from '@/views/question/config'
export default {
  name: 'testQuestion',
  data () {
    return {
      QUESTION_TYPE,
      CONTENT_TYPE,
      QUESTION_LEVEL,
      CANDIDATE_TYPE,
      loading: false,
      queryId: this.$route.query['id'],
      form: {
        difficulty: QUESTION_LEVEL['LOW'],
        type: QUESTION_TYPE['RADIO'],
        candidate_type: CANDIDATE_TYPE['SPLIT'],
        desc: '',
        question: [],
        candidate: {},
        candidate_group: []
      },
      answer: {}
    }
  },
  props: {
    // isActive: {
    //   type: Boolean,
    //   default: false
    // },
    detailId: {
      type: String,
      default: null
    },
    userResponse: {
      type: Object,
      default: null
    }
  },
  created () {
    // console.log(this.$route.query)
    // isActive
    // console.log(this.isActive)//
    /**
     * 这个组件（components）test.vue有三处地方用到
     * 1.从题目列表通过$route.push跳转过来,测试答题的，会在$route.query带上要测试的题目id，
     * 2.从测试题目菜单进入，需要请求firstquestion接口获取题目
     * 3.从result列表查看答题详情，会通过props把question_id还有user_response传过来
     * showQuestion接口是通过question_id获取question
     * firstQuestion是获取irt答题的选题结果
     */
    let questionId = this.detailId || this.queryId
    if (questionId) {
      this.loading = true
      showQuestion(questionId).then(({ res, err }) => {
        this.loading = false
        if (!err) {
          this.handleSetForm(res)
          if (this.userResponse) {
            // 答案的template里面的答案是由data里面的answer保存着的，所以把props的userResponse赋值给answer，页面上就会把对应的选项对应了
            this.$set(this, 'answer', this.userResponse)
          }
        }
      })
    } else {
      // alert('------')
      this.loading = true
      firstQuestion().then(({ res, err }) => {
        this.loading = false
        if (!err) {
          this.handleSetForm(res)
        }
      })
    }
  },
  computed: {
    isSplitCandidate () {
      return Number(this.form.candidate_type) === Number(CANDIDATE_TYPE['SPLIT'])
    },
    preview () {
      return JSON.stringify(this.form, null, 6)
    }
  },
  methods: {
    testUser () {
      getUser().then(({ res, err }) => {
        if (!err) {
          alert(JSON.stringify(res))
        }
      })
    },
    handleSetForm (data) {
      this.$set(this, 'form', Object.assign(this.form, data))
      this.$set(this, 'answer', {})
      let _answer_type = this.getAnswerType()
      for (let q of this.form['question']) {
        this.$set(this.answer, q['num'], _answer_type)
      }
    },
    getCandidate (question) { // 根据不同的选项类型，去展示答案列表
      if (this.form['type'] === QUESTION_TYPE['INPUT']) {
        return []
      } else if (this.isSplitCandidate) {
        return this.form.candidate[question['num']] || []
      } else {
        return this.form.candidate_group
      }
    },
    getAnswerType () { // 获取答案的类型，因为不同类型的题目答案类型不一样
      switch (this.form['type']) {
        case QUESTION_TYPE['RADIO']:
          return ''
        case QUESTION_TYPE['CHECKBOX']:
          return []
        case QUESTION_TYPE['INPUT']:
          return ''
        default:
          return ''
      }
    },
    submitForm () {
      this.$refs['form'].validate((valid) => {
        if (!valid) return false
        this.loading = true
        nextQuestion({ answer: this.answer }).then(({ res, err }) => {
          this.loading = false
          if (!err) {
            // 判断是否停止
            if (res.stop) {
              alert(res.message)
              this.$router.push({
                name: 'ExamResult',
                params: { exam_result: [res.result] }
              })
            } else {
              // todo,,加上提示信息
              // 设置form，页面回答下一题
              this.handleSetForm(res)
              this.$refs['form'].clearValidate()// 清除表单校验提示效果
            }
            this.utils.successMsg()
          }
        })
      })
    }
  }
}
</script>

<style lang="less">
.m-question-test {
  .el-table {
    .candidate-col {
      .cell {
        flex-direction: column;
        align-items: baseline;
      }
    }
  }
  .el-form .el-form-item {
    .el-radio-button--mini .el-radio-button__inner {
      padding: 5px;
    }
    .split-pane,
    .split-pane2 {
      background: #fdf6ec;
      margin-bottom: 5px;
      padding: 5px;
      .el-select {
        .el-input {
          width: 100px;
        }
      }
    }
    .split-pane2 {
      padding: 0 5px;
    }
  }
}
</style>
