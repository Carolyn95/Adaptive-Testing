<template>
  <el-menu class="navbar" mode="horizontal">
    <hamburger class="hamburger-container" :toggleClick="toggleSideBar" :isActive="sidebar.opened"></hamburger>
    <router-link to="/">
      <p class="title">后台</p>
    </router-link>
  <div class="right-menu">
      <el-dropdown class="avatar-container right-menu-item" trigger="click">
        <div class="content">
          <div class="avatar-wrapper">
            {{user_info && user_info.username}}
            <i class="el-icon-caret-bottom"></i>
          </div>
        </div>
        <el-dropdown-menu class="user-dropdown" slot="dropdown">
          <span @click="logout">
            <el-dropdown-item divided>退出登陆</el-dropdown-item>
          </span>
        </el-dropdown-menu>
      </el-dropdown>
    </div>
  </el-menu>
</template>

<script>
import { mapGetters } from 'vuex'
import Hamburger from '@/components/Hamburger'

export default {
  name: 'navBar',
  components: {
    Hamburger
  },
  computed: {
    ...mapGetters([
      'sidebar', 'user_info',
      'sysNotice'
    ])
  },
  data () {
    return {
    }
  },
  methods: {
    toggleSideBar () {
      this.$store.dispatch('ToggleSideBar')
    },
    logout () {
      let loadingInstance = this.$loading()
      this.$store.dispatch('LogOut').then(() => {
        loadingInstance.close()
        location.reload()
      }).catch(() => {
        loadingInstance.close()
      })
    }
  }
}
</script>

<style rel="stylesheet/scss" lang="scss">
.navbar {
  position: sticky;
  top: 0;
  width: 100%;
  min-height: 50px;
  line-height: 50px;
  // position: fixed;
  background: #fff;
  z-index: 100;
  border-radius: 0px !important;
  .hamburger-container {
    line-height: 58px;
    height: 50px;
    float: left;
    padding: 0 10px;
  }
  .el-badge__content {
    top: 10px;
  }
  .el-badge {
    margin: 0px 15px;
  }

  .right-menu {
    float: right;
    height: 100%;
    &:focus {
      outline: none;
    }
    .right-menu-item {
      display: inline-block;
      margin: 0 8px;
    }
    .avatar-container {
      margin-right: 30px;
      .avatar-wrapper {
        cursor: pointer;
        position: relative;
        font-size: 16px;
        .el-icon-caret-bottom {
          position: absolute;
          right: -15px;
          top: 20px;
          font-size: 12px;
        }
      }
    }
  }
  .title {
    float: left;
    width: 130px;
    text-align: center;
    font-size: 26px;
    font-weight: 600;
    color:#000;
  }
  .el-checkbox {
    .el-checkbox__label {
      padding: 2px;
    }
  }
}
</style>
